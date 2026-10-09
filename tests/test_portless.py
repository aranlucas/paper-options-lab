import http.client
import json
import os
import threading
import unittest
from http.server import HTTPServer
from unittest.mock import patch
from urllib.parse import urlsplit

from options_lab.fixtures import START, fixture, iso
from options_lab.server import Handler, portless_origin


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class PortlessOriginTests(unittest.TestCase):
    def test_unset_origin_preserves_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(portless_origin())

    def test_exact_local_origins_and_worktrees(self):
        for origin in (
            "https://paper-options-lab.localhost",
            "https://feature.paper-options-lab.localhost",
            "http://paper-options-lab.localhost:14480",
        ):
            with self.subTest(origin=origin), patch.dict(os.environ, {"PORTLESS_URL": origin}):
                self.assertEqual(portless_origin(), origin)


class PortlessHTTPTests(unittest.TestCase):
    def setUp(self):
        self.origin = "https://feature.paper-options-lab.localhost"
        self.server = HTTPServer(("127.0.0.1", 0), QuietHandler)
        self.server.public_origin = self.origin
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path="/api/health", method="GET", headers=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, json.loads(data)

    def test_configured_host_serves_health_and_analysis(self):
        headers = {"Host": urlsplit(self.origin).netloc, "Origin": self.origin}
        status, data = self.request(headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(data["execution"], "absent")
        headers["Content-Type"] = "application/json"
        body = json.dumps({"dataset": fixture("rally"), "at": iso(START), "quantity": 1, "policy": {}})
        status, data = self.request("/api/analyze", "POST", headers, body)
        self.assertEqual(status, 200)
        self.assertTrue(data["replay"]["paper_only"])

    def test_unconfigured_hosts_and_forwarded_headers_are_rejected(self):
        for host in ("evil.invalid", "other.paper-options-lab.localhost", "paper-options-lab.localhost"):
            with self.subTest(host=host):
                status, _ = self.request(headers={"Host": host, "X-Forwarded-Host": urlsplit(self.origin).netloc})
                self.assertEqual(status, 403)

    def test_wrong_origin_remains_rejected(self):
        for origin in ("https://evil.invalid", "https://other.paper-options-lab.localhost", "http://feature.paper-options-lab.localhost"):
            with self.subTest(origin=origin):
                status, _ = self.request("/api/analyze", "POST", {
                    "Host": urlsplit(self.origin).netloc,
                    "Origin": origin,
                    "Content-Type": "application/json",
                }, "{}")
                self.assertEqual(status, 403)

    def test_default_loopback_still_works(self):
        status, _ = self.request()
        self.assertEqual(status, 200)
        self.server.public_origin = None
        status, _ = self.request(headers={"Host": urlsplit(self.origin).netloc})
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
