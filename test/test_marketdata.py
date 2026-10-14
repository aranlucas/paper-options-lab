import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from options_lab.engine import Policy, compare, replay
from options_lab.marketdata import convert_marketdata
from options_lab.provider_fixtures import marketdata_fixture
from options_lab.schema import InputError, timestamp, validate_dataset
from options_lab.__main__ import read_input

ROOT = Path(__file__).resolve().parent.parent


class MarketDataTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.meta = marketdata_fixture()

    def convert(self, at=None):
        return convert_marketdata(self.packet, self.meta, at)

    def test_historical_nulls_remain_unknown_and_input_is_immutable(self):
        original = deepcopy((self.packet, self.meta))
        result = self.convert()
        self.assertEqual((self.packet, self.meta), original)
        validate_dataset(result["dataset"])
        self.assertTrue(result["dataset"]["source"]["observation_only"])
        self.assertEqual(result["dataset"]["events"], [])
        self.assertEqual(result["dataset"]["settlements"], [])
        for quote, audit in zip(result["dataset"]["snapshots"][0]["contracts"], result["audit"]["contracts"]):
            self.assertIsNone(quote["iv"])
            self.assertEqual(audit["provider_greeks"], dict.fromkeys(("delta", "gamma", "theta", "vega")))
            self.assertIn("MISSING_IV", audit["screen_reasons"])
            self.assertIn("STALE_QUOTE", audit["screen_reasons"])

    def test_latest_supplied_iv_is_preserved_but_never_inferred_from_greeks(self):
        self.packet, self.meta = marketdata_fixture("latest_eod")
        result = self.convert()
        self.assertEqual(result["dataset"]["snapshots"][0]["contracts"][0]["iv"], .25)
        self.assertEqual(result["audit"]["contracts"][0]["provider_greeks"]["delta"], self.packet["delta"][0])
        del self.packet["iv"]
        result = self.convert()
        self.assertIsNone(result["dataset"]["snapshots"][0]["contracts"][0]["iv"])
        self.assertIn("MISSING_IV", result["audit"]["contracts"][0]["screen_reasons"])

    def test_observation_gate_blocks_fills_even_with_relaxed_freshness(self):
        self.packet, self.meta = marketdata_fixture("latest_eod")
        data = self.convert()["dataset"]
        at = self.meta["retrieved_at"]
        data["events"] = [{"at": at, "action": "open", "long_id": self.packet["optionSymbol"][0], "short_id": self.packet["optionSymbol"][1], "quantity": 1}]
        relaxed = Policy(max_quote_age_seconds=1000000, max_liquidity_age_seconds=1000000)
        self.assertEqual(compare(data, at, relaxed)["error"], "OBSERVATION_ONLY_DATA")
        result = replay(data, relaxed)
        self.assertEqual(result["cash"], relaxed.capital)
        self.assertEqual(result["open_positions"], [])
        self.assertEqual(result["ledger"][0]["reasons"], ["OBSERVATION_ONLY_DATA"])
        self.assertIn("no performance backtest", result["label"])

    def test_missing_fields_and_zero_values_are_not_filled(self):
        for field in ("bid", "ask", "bidSize", "askSize", "volume", "openInterest", "iv", "delta"):
            self.packet.pop(field, None)
        self.meta["open_interest_available_at"] = None
        result = self.convert()
        quote = result["dataset"]["snapshots"][0]["contracts"][0]
        self.assertTrue(all(quote[field] is None for field in ("bid", "ask", "bid_size", "ask_size", "volume", "open_interest", "iv")))
        self.packet["bid"] = [0] * 4
        self.packet["ask"] = [1] * 4
        self.assertIn("ZERO_OR_CROSSED_MARKET", self.convert()["audit"]["contracts"][0]["screen_reasons"])

    def test_crossed_wide_and_insufficient_size_are_diagnosed(self):
        self.packet["bid"][0] = 100
        self.packet["ask"][1] = 100
        self.packet["bidSize"][2] = 0
        rows = self.convert()["audit"]["contracts"]
        self.assertIn("ZERO_OR_CROSSED_MARKET", rows[0]["screen_reasons"])
        self.assertIn("WIDE_SPREAD", rows[1]["screen_reasons"])
        self.assertIn("INSUFFICIENT_DISPLAYED_SIZE", rows[2]["screen_reasons"])

    def test_schema_status_lengths_unknown_keys_and_packet_limits(self):
        for mutate in (lambda p: p.update(s="no_data"), lambda p: p.update(bid=[1]), lambda p: p.update(token="forbidden"), lambda p: p.update(optionSymbol=[None]*4), lambda p: p.update(optionSymbol=p["optionSymbol"]*7)):
            with self.subTest(mutate=mutate):
                packet = deepcopy(self.packet); mutate(packet)
                with self.assertRaises(InputError): convert_marketdata(packet, self.meta)

    def test_occ_identity_rejects_bad_dates_sides_strikes_and_aliases(self):
        for field, value in (("optionSymbol", "DEMO260230C00100000"), ("optionSymbol", "bad-symbol"), ("side", "put"), ("strike", 101), ("expiration", self.packet["expiration"][0]+86400)):
            packet = deepcopy(self.packet); packet[field][0] = value
            meta = deepcopy(self.meta)
            if field == "optionSymbol": meta["contracts"][value] = meta["contracts"].pop(self.packet["optionSymbol"][0])
            with self.subTest(field=field,value=value), self.assertRaises(InputError): convert_marketdata(packet,meta)
        original = self.packet["optionSymbol"][0]
        alias = original.replace("DEMO", "DEMO  ", 1)
        self.packet["optionSymbol"][1] = alias
        self.packet["side"][1] = "call"; self.packet["strike"][1] = 100
        self.meta["contracts"].pop(next(key for key in self.meta["contracts"] if key != original))
        self.meta["contracts"][alias] = deepcopy(self.meta["contracts"][original])
        with self.assertRaises(InputError): self.convert()

    def test_contract_metadata_is_required_and_not_guessed(self):
        symbol = self.packet["optionSymbol"][0]
        for field, value in (("root", "SPXW"), ("underlying", "OTHER"), ("exercise", "unknown"), ("settlement", "unknown"), ("multiplier", True), ("adjusted", "false"), ("reference", ""), ("last_trade_at", "2030-01-01T00:00:00Z")):
            meta=deepcopy(self.meta); meta["contracts"][symbol][field]=value
            with self.subTest(field=field), self.assertRaises(InputError): convert_marketdata(self.packet,meta)
        self.meta["contracts"].pop(symbol)
        with self.assertRaises(InputError): self.convert()

    def test_american_physical_and_adjusted_survive_import_but_are_rejected(self):
        spec=self.meta["contracts"][self.packet["optionSymbol"][0]]
        spec.update(exercise="american",settlement="physical",adjusted=True)
        result=self.convert()
        row=result["dataset"]["snapshots"][0]["contracts"][0]
        self.assertEqual(row["exercise"],"american")
        for code in ("EARLY_ASSIGNMENT_UNSUPPORTED","PHYSICAL_DELIVERY_UNSUPPORTED","ADJUSTED_DELIVERABLE_UNSUPPORTED"):
            self.assertIn(code,result["audit"]["contracts"][0]["screen_reasons"])

    def test_future_and_stale_metadata_and_delay_constraints(self):
        as_of=timestamp(self.meta["inputs_available_at"])
        for field,value in (("retrieved_at",as_of.isoformat()),("retrieved_at","2026-10-03T20:00:00"),("inputs_available_at",(as_of+timedelta(seconds=1)).isoformat()),("open_interest_available_at",None),("open_interest_available_at",(as_of+timedelta(seconds=1)).isoformat()),("open_interest_available_at",(as_of-timedelta(days=2)).isoformat()),("source",[])):
            meta=deepcopy(self.meta); meta[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(InputError):convert_marketdata(self.packet,meta)
        at=as_of.isoformat()
        reasons=self.convert(at)["audit"]["contracts"][0]["screen_reasons"]
        self.assertIn("SNAPSHOT_NOT_YET_AVAILABLE",reasons)

    def test_historical_iv_and_nonfinite_or_percentage_inputs_fail_closed(self):
        for field,value in (("iv",.25),("delta",.5),("bid",float("nan")),("volume",1.5),("updated",self.packet["updated"][0]+.5)):
            packet=deepcopy(self.packet); packet[field][0]=value
            with self.subTest(field=field),self.assertRaises(InputError):convert_marketdata(packet,self.meta)
        self.packet,self.meta=marketdata_fixture("latest_eod")
        self.packet["iv"][0]=25
        with self.assertRaises(InputError):self.convert()

    def test_unix_instants_and_dst_are_not_reinterpreted_as_wall_clock(self):
        for at in (datetime(2026,10,2,20,tzinfo=timezone.utc),datetime(2026,11,2,21,tzinfo=timezone.utc)):
            packet,meta=marketdata_fixture(at=at)
            result=convert_marketdata(packet,meta)
            self.assertEqual(timestamp(result["dataset"]["snapshots"][0]["as_of"]),at)
            packet["updated"]=[int(at.replace(hour=16).timestamp())]*4
            with self.assertRaises(InputError):convert_marketdata(packet,meta)

    def test_unsynchronized_rows_spots_and_dates_are_not_combined(self):
        for field,value in (("updated",self.packet["updated"][0]-1),("underlyingPrice",101),("underlying","OTHER")):
            packet=deepcopy(self.packet);packet[field][0]=value
            with self.subTest(field=field),self.assertRaises(InputError):convert_marketdata(packet,self.meta)
        self.meta["request_date"]="2026-10-01"
        with self.assertRaises(InputError):self.convert()

    def test_expiration_time_uses_manifest_and_discloses_provider_difference(self):
        result=self.convert()
        quote=result["dataset"]["snapshots"][0]["contracts"][0]
        self.assertEqual(quote["expires_at"],self.meta["contracts"][quote["id"]]["expires_at"])
        self.assertIn("PROVIDER_EXPIRATION_TIME_DIFFERS",result["audit"]["contracts"][0]["warnings"])

    def test_saved_fixtures_and_cli_are_reproducible(self):
        for name in ("historical","latest_eod"):
            packet,meta=marketdata_fixture(name)
            prefix=ROOT/"fixtures"/"providers"/f"marketdata-{name}"
            self.assertEqual(json.loads(prefix.with_suffix(".json").read_text()),packet)
            self.assertEqual(json.loads(prefix.with_suffix(".meta.json").read_text()),meta)
        args=[sys.executable,"-m","options_lab","import-marketdata","--input",str(ROOT/"fixtures/providers/marketdata-historical.json"),"--metadata",str(ROOT/"fixtures/providers/marketdata-historical.meta.json")]
        result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,check=True)
        self.assertTrue(validate_dataset(json.loads(result.stdout))["source"]["observation_only"])
        args[3]="audit-marketdata"
        report=json.loads(subprocess.run(args,cwd=ROOT,capture_output=True,text=True,check=True).stdout)
        self.assertEqual(report["fills_created"],0)
        missing=subprocess.run([sys.executable,"-m","options_lab","import-marketdata"],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(missing.returncode,2)

    def test_observation_flag_cannot_be_a_false_or_truthy_nonboolean_value(self):
        data=self.convert()["dataset"]
        for value in (False,1,"true",None):
            data["source"]["observation_only"]=value
            with self.subTest(value=value),self.assertRaises(InputError):validate_dataset(data)

    def test_cli_file_size_and_utf8_are_bounded_before_json_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"input.json"
            path.write_bytes(b' '*(2*1024*1024+1))
            with self.assertRaises(InputError):read_input(path)
            path.write_bytes(b'\xff')
            with self.assertRaises(ValueError):read_input(path)


if __name__ == "__main__":
    unittest.main()
