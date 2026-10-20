import unittest

from MOBILE_APP.endpoint_selection import (
    can_fail_over_automatically,
    endpoint_candidates,
    normalize_endpoint,
)


class EndpointSelectionTests(unittest.TestCase):
    def test_lan_precedes_tailscale(self):
        self.assertEqual(
            endpoint_candidates("http://192.168.1.20:8765", "http://100.64.0.4:8765"),
            ["http://192.168.1.20:8765", "http://100.64.0.4:8765"],
        )

    def test_empty_and_duplicate_endpoints(self):
        self.assertEqual(endpoint_candidates("", "http://100.64.0.4:8765"), ["http://100.64.0.4:8765"])
        self.assertEqual(endpoint_candidates("http://pc.local:8765", "http://pc.local:8765"), ["http://pc.local:8765"])

    def test_rejects_credentials_and_paths(self):
        for url in ("ftp://pc:8765", "http://user:pass@pc:8765", "http://pc:8765/api", "http://pc:8765/?token=x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_endpoint(url)

    def test_never_fail_over_write_requests(self):
        self.assertTrue(can_fail_over_automatically("GET"))
        for method in ("POST", "PUT", "PATCH", "DELETE", ""):
            with self.subTest(method=method):
                self.assertFalse(can_fail_over_automatically(method))


if __name__ == "__main__":
    unittest.main()
