import json
import unittest
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

from options_lab.engine import Policy, compare, evaluate_pair, policy_from_dict, replay
from options_lab.fixtures import EXPIRY, SCENARIOS, START, fixture, iso
from options_lab.pricing import analytical
from options_lab.schema import InputError, load_json, timestamp, validate_dataset


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture("rally")
        self.snapshot = self.data["snapshots"][0]
        self.long = next(q for q in self.snapshot["contracts"] if q["id"] == "DEMO-call-100")
        self.short = next(q for q in self.snapshot["contracts"] if q["id"] == "DEMO-call-105")

    def pair(self, policy=None, qty=1):
        return evaluate_pair(self.long, self.short, self.snapshot, START, policy or Policy(), qty)

    def test_known_black_scholes_value_and_greek_units(self):
        call = analytical("call", 100, 100, 1, .2, .05, 0)
        put = analytical("put", 100, 100, 1, .2, .05, 0)
        self.assertAlmostEqual(call["price"], 10.45058357, places=7)
        self.assertAlmostEqual(put["price"], 5.57352602, places=7)
        self.assertAlmostEqual(call["delta"], .63683065, places=7)
        eps=.001
        higher=analytical("call",100+eps,100,1,.2,.05,0)
        lower=analytical("call",100-eps,100,1,.2,.05,0)
        self.assertAlmostEqual(call["delta"],(higher["price"]-lower["price"])/(2*eps),places=7)
        self.assertAlmostEqual(call["gamma"],(higher["delta"]-lower["delta"])/(2*eps),places=7)
        self.assertAlmostEqual(call["vega"], .3752403469, places=7)

    def test_defined_payoff_bounds_and_cost_accounting(self):
        c = self.pair()
        self.assertTrue(c["eligible"])
        self.assertAlmostEqual(c["max_loss"], c["debit"]+c["entry_fees"]+c["reserved_exit_fees"], places=2)
        self.assertAlmostEqual(c["expiry_max_profit"] + c["expiry_max_loss"], 500, places=2)
        self.assertEqual(c["slippage_cost"],4)
        for p in c["payoff"]:
            self.assertGreaterEqual(p["pnl"],-c["max_loss"])
            self.assertLessEqual(p["pnl"],c["expiry_max_profit"])
        point = next(p for p in c["payoff"] if abs(p["spot"]-c["break_even"])<.0001)
        self.assertAlmostEqual(point["pnl"],0,places=2)

    def test_multiplier_and_quantity_scale_every_dollar_and_greek(self):
        one=self.pair()
        self.long["multiplier"]=self.short["multiplier"]=10
        mini=self.pair(qty=2)
        self.assertAlmostEqual(mini["debit"],one["debit"]*.2,places=1)
        self.assertAlmostEqual(mini["greeks"]["delta"],one["greeks"]["delta"]*.2,places=5)
        self.assertEqual(mini["entry_fees"],2.6)
        self.short["multiplier"]=100
        self.assertIn("MISMATCH_MULTIPLIER",self.pair()["reasons"])

    def test_missing_stale_crossed_wide_and_size_fail_closed(self):
        mutations=[("bid",None,"MISSING_QUOTE"),("quote_at",iso(START-timedelta(minutes=3)),"STALE_QUOTE"),("bid",1000,"ZERO_OR_CROSSED_MARKET"),("ask",20,"WIDE_SPREAD"),("ask_size",0,"INSUFFICIENT_DISPLAYED_SIZE"),("volume",1,"LOW_LIQUIDITY"),("iv",None,"MISSING_IV"),("open_interest",None,"MISSING_LIQUIDITY")]
        for field,value,expected in mutations:
            with self.subTest(field=field,value=value):
                original=self.long[field];self.long[field]=value
                c=self.pair();self.assertFalse(c["eligible"]);self.assertIn(f"LONG:{expected}",c["reasons"])
                self.long[field]=original

    def test_timestamp_checks_and_stale_underlying(self):
        self.long["quote_at"]=iso(START+timedelta(seconds=1))
        self.assertIn("LONG:FUTURE_QUOTE_OR_LIQUIDITY",self.pair()["reasons"])
        self.long["quote_at"]=iso(START)
        self.long["liquidity_at"]=iso(START+timedelta(seconds=1))
        self.assertIn("LONG:FUTURE_QUOTE_OR_LIQUIDITY",self.pair()["reasons"])
        self.long["liquidity_at"]=iso(START)
        self.snapshot["spot_at"]=iso(START-timedelta(minutes=3))
        self.assertIn("LONG:STALE_UNDERLYING",self.pair()["reasons"])
        self.snapshot["spot_at"]=iso(START)
        self.snapshot["available_at"]=iso(START+timedelta(seconds=10))
        self.assertIn("LOOKAHEAD_OR_INVALID_AVAILABILITY",self.pair()["reasons"])
        self.assertEqual(compare(self.data,iso(START),snapshot_id="entry")["error"],"LOOKAHEAD_OR_INVALID_AVAILABILITY")

    def test_asynchronous_legs(self):
        self.long["quote_at"]=iso(START-timedelta(seconds=10))
        self.assertIn("ASYNCHRONOUS_LEGS",self.pair()["reasons"])

    def test_american_physical_and_adjusted_rejected(self):
        self.long.update(exercise="american",settlement="physical",adjusted=True)
        reasons=self.pair()["reasons"]
        for code in ("EARLY_ASSIGNMENT_UNSUPPORTED","PHYSICAL_DELIVERY_UNSUPPORTED","ADJUSTED_DELIVERABLE_UNSUPPORTED"):
            self.assertIn(f"LONG:{code}",reasons)

    def test_dte_and_trading_cutoff(self):
        self.long["last_trade_at"]=iso(START)
        self.assertIn("LONG:CONTRACT_NOT_TRADABLE",self.pair()["reasons"])
        self.long["last_trade_at"]=self.long["expires_at"]=iso(START+timedelta(days=2))
        self.assertIn("LONG:DTE_OUTSIDE_WINDOW",self.pair()["reasons"])

    def test_position_cash_quantity_delta_caps(self):
        for policy,code in ((Policy(max_loss_per_position=10),"POSITION_RISK_LIMIT"),(Policy(capital=10),"CAPITAL_LIMIT"),(Policy(max_abs_delta=.1),"DELTA_LIMIT")):
            self.assertIn(code,self.pair(policy)["reasons"])
        self.assertIn("QUANTITY_LIMIT",self.pair(qty=3)["reasons"])

    def test_portfolio_caps_and_no_partial_fills(self):
        result=replay(self.data,Policy(max_positions=1))
        self.assertEqual(sum(r["action"]=="PAPER_OPENED" for r in result["ledger"]),1)
        self.assertTrue(any("POSITION_COUNT_LIMIT" in r.get("reasons",[]) for r in result["ledger"]))
        self.assertTrue(any("PORTFOLIO_RISK_LIMIT" in r.get("reasons",[]) for r in replay(self.data,Policy(max_portfolio_risk=10))["ledger"]))
        self.assertTrue(any("PORTFOLIO_DELTA_LIMIT" in r.get("reasons",[]) for r in replay(self.data,Policy(max_abs_delta=10))["ledger"]))
        empty=replay(self.data,Policy(capital=1))
        self.assertEqual(empty["cash"],1)
        self.assertEqual(empty["realized_pnl"],0)
        self.assertEqual(empty["open_positions"],[])

    def test_settlement_value_not_spot_and_not_future_information(self):
        base=replay(self.data)
        changed=deepcopy(self.data);changed["settlements"][0]["value"]=1
        down=replay(changed)
        opened=lambda r:[row for row in r["ledger"] if row["action"]=="PAPER_OPENED"]
        self.assertEqual(opened(base),opened(down))
        self.assertNotEqual(base["realized_pnl"],down["realized_pnl"])
        self.assertEqual(base["cash"],round(Policy().capital+base["realized_pnl"],2))
        changed["settlements"][0]["available_at"]=iso(EXPIRY+timedelta(hours=1))
        pending=replay(changed)
        self.assertFalse(pending["complete"])
        self.assertIsNone(pending["equity"])
        self.assertGreater(pending["reserved_risk"],0)

    def test_missing_settlement_preserves_reserved_exposure(self):
        r=replay(fixture("pending"))
        self.assertEqual(len(r["open_positions"]),3)
        self.assertIsNone(r["equity"])
        self.assertGreater(r["reserved_risk"],0)
        self.assertEqual(r["realized_pnl"],0)

    def test_replay_cutoff_excludes_future_events_and_does_not_mutate_input(self):
        original = deepcopy(self.data)
        before = replay(self.data, through=iso(START))
        self.assertEqual(before["cash"], Policy().capital)
        self.assertEqual(before["open_positions"], [])
        self.assertEqual(before["realized_pnl"], 0)
        after_one = replay(self.data, through=iso(START + timedelta(seconds=1)))
        self.assertEqual(len(after_one["open_positions"]), 1)
        self.assertIsNone(after_one["equity"])
        self.assertGreater(after_one["reserved_risk"], 0)
        self.assertTrue(all(timestamp(row["at"]) <= START + timedelta(seconds=1) for row in after_one["ledger"]))
        self.assertEqual(self.data, original)

    def test_replay_cutoff_requires_available_official_settlement(self):
        before = replay(self.data, through=iso(EXPIRY + timedelta(seconds=29)))
        self.assertEqual(len(before["open_positions"]), 3)
        self.assertIsNone(before["equity"])
        self.assertEqual(before["realized_pnl"], 0)
        available = replay(self.data, through=iso(EXPIRY + timedelta(seconds=30)))
        self.assertTrue(available["complete"])
        self.assertEqual(available["open_positions"], [])
        self.assertEqual(available["cash"], replay(self.data)["cash"])
        self.assertEqual(sum(row["action"] == "PAPER_SETTLED" for row in available["ledger"]), 3)
        pending = replay(fixture("pending"), through=iso(EXPIRY + timedelta(days=1)))
        self.assertIsNone(pending["equity"])
        self.assertEqual(len(pending["open_positions"]), 3)

    def test_replay_cutoff_is_timezone_aware_and_equivalent_to_full_window(self):
        with self.assertRaises(InputError):
            replay(self.data, through="2026-10-02T14:00:00")
        full = replay(self.data)
        bounded = replay(self.data, through=self.data["events"][-1]["at"])
        self.assertEqual(full["ledger"], bounded["ledger"])
        self.assertEqual(full["cash"], bounded["cash"])
        self.assertEqual(full["reserved_risk"], bounded["reserved_risk"])

    def test_early_close_charges_both_sides_and_releases_risk(self):
        result=replay(fixture("vol-crush"))
        closed=[row for row in result["ledger"] if row["action"]=="PAPER_CLOSED"]
        self.assertEqual(len(closed),1)
        self.assertEqual(closed[0]["fees"],1.3)
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["cash"]-Policy().capital,result["realized_pnl"],places=2)

    def test_all_fixture_payoffs_bounded_and_replay_deterministic(self):
        for scenario in ("rally","selloff","flat","vol-crush","stale","missing","pending"):
            data=fixture(scenario)
            r=replay(data)
            self.assertEqual(json.dumps(r,sort_keys=True),json.dumps(replay(data),sort_keys=True))
            for c in compare(data,iso(START))["candidates"]:
                if c.get("payoff"):
                    self.assertTrue(all(-c["max_loss"]<=p["pnl"]<=c["expiry_max_profit"] for p in c["payoff"]))
            for row in r["ledger"]:
                self.assertGreaterEqual(row["cash"],0)
                self.assertLessEqual(row["reserved_risk"],Policy().max_portfolio_risk)
                self.assertTrue(row["paper_only"])

    def test_saved_fixtures_reproduce_generator_exactly(self):
        root = Path(__file__).resolve().parent.parent / "fixtures"
        for name in SCENARIOS:
            saved = validate_dataset(load_json((root / f"{name}.json").read_text()))
            self.assertEqual(saved, fixture(name), name)

    def test_indicative_feed_rejected(self):
        self.data["source"].update(kind="imported",feed="indicative")
        self.assertEqual(compare(self.data,iso(START))["error"],"NON_EXECUTABLE_OR_UNKNOWN_FEED")
        self.assertFalse(any(r["action"]=="PAPER_OPENED" for r in replay(self.data)["ledger"]))

    def test_no_available_snapshot(self):
        self.assertEqual(compare(self.data,iso(START-timedelta(seconds=1)))["error"],"NO_AVAILABLE_CHAIN")

    def test_strict_input_validation(self):
        for mutate in (
            lambda d:d["snapshots"][0].update(spot=float("nan")),
            lambda d:d["snapshots"][0].update(as_of="2026-10-02T14:00:00"),
            lambda d:d["events"].reverse(),
            lambda d:d.update(broker_key="must reject"),
            lambda d:d["snapshots"][0]["contracts"].append(deepcopy(d["snapshots"][0]["contracts"][0])),
            lambda d:d["snapshots"][1]["contracts"][0].update(multiplier=10),
            lambda d:d["settlements"][0].update(method="stock_close"),
            lambda d:d["events"][0].update(action="submit_order"),
        ):
            data=deepcopy(self.data);mutate(data)
            with self.assertRaises(InputError):validate_dataset(data)
        with self.assertRaises(InputError):load_json('{"x": NaN}')
        for values in ({"max_positions":1.5},{"slippage_points":-1},{"capital":True},{"broker_url":"x"}):
            with self.assertRaises(InputError):policy_from_dict(values)


if __name__ == "__main__":
    unittest.main()
