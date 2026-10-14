import http.client
import json
import threading
import unittest
from http.server import HTTPServer

from options_lab.fixtures import START, fixture, iso
from options_lab.server import Handler
from options_lab.marketdata import convert_marketdata
from options_lab.provider_fixtures import marketdata_fixture


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class LocalAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=HTTPServer(("127.0.0.1",0),QuietHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def request(self,path,method="GET",body=None,headers=None):
        connection=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=5)
        connection.request(method,path,body=body,headers=headers or {})
        response=connection.getresponse()
        status=response.status;data=response.read();connection.close()
        return status,json.loads(data)

    def test_health_exposes_execution_absence(self):
        status,data=self.request("/api/health")
        self.assertEqual(status,200)
        self.assertEqual(data["execution"],"absent")
        self.assertTrue(data["paper_only"])

    def test_no_order_endpoint(self):
        status,_=self.request("/api/order","POST",'{}',{"Content-Type":"application/json"})
        self.assertEqual(status,404)

    def test_analyze_import_and_fail_closed(self):
        body=json.dumps({"dataset":fixture("rally"),"at":iso(START),"quantity":1,"policy":{}})
        status,data=self.request("/api/analyze","POST",body,{"Content-Type":"application/json"})
        self.assertEqual(status,200)
        self.assertGreater(data["comparison"]["eligible_count"],0)
        self.assertTrue(data["replay"]["paper_only"])
        status,data=self.request("/api/analyze","POST",'{"dataset": null}',{"Content-Type":"application/json"})
        self.assertEqual(status,400)
        self.assertIn("error",data)

    def test_cross_origin_and_host_rejected(self):
        body='{}'
        status,_=self.request("/api/analyze","POST",body,{"Content-Type":"application/json","Origin":"https://evil.invalid"})
        self.assertEqual(status,403)
        status,_=self.request("/api/health",headers={"Host":"evil.invalid"})
        self.assertEqual(status,403)

    def test_offline_provider_import_stays_observation_only_in_dashboard_api(self):
        packet,manifest=marketdata_fixture("latest_eod")
        dataset=convert_marketdata(packet,manifest)["dataset"]
        body=json.dumps({"dataset":dataset,"at":manifest["retrieved_at"],"quantity":1,"policy":{"max_quote_age_seconds":1000000}})
        status,data=self.request("/api/analyze","POST",body,{"Content-Type":"application/json"})
        self.assertEqual(status,200)
        self.assertEqual(data["comparison"]["error"],"OBSERVATION_ONLY_DATA")
        self.assertEqual(data["replay"]["open_positions"],[])
        self.assertIn("no performance backtest",data["replay"]["label"])

    def test_invalid_json_duplicate_keys_and_size(self):
        for body in ('{','{"dataset":null,"dataset":null}'):
            status,_=self.request("/api/analyze","POST",body,{"Content-Type":"application/json"})
            self.assertEqual(status,400)
        status,_=self.request("/api/analyze","POST",'{}',{"Content-Type":"text/plain"})
        self.assertEqual(status,415)
        status,_=self.request("/api/analyze","POST",'',{"Content-Type":"application/json","Content-Length":"3000000"})
        self.assertEqual(status,413)

    def test_no_local_file_exposure(self):
        status,_=self.request("/../requirements.txt")
        self.assertEqual(status,404)
        status,_=self.request("/.venv/pyvenv.cfg")
        self.assertEqual(status,404)


if __name__ == "__main__":
    unittest.main()
