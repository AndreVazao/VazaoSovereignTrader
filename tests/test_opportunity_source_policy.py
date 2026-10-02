from __future__ import annotations

import unittest

from PC_ENGINE.opportunity.source_policy import OfficialSourcePolicy


class OfficialSourcePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = OfficialSourcePolicy(frozenset({"www.binance.com", "support.coinbase.com"}))
        self.digest = "a" * 64

    def observation(self, **overrides):
        values = {
            "source_url": "https://WWW.BINANCE.COM/en/support/faq?x=1",
            "observed_at_ms": 1_000,
            "source_captured_at_ms": 900,
            "evidence_sha256": self.digest,
            "now_ms": 2_000,
        }
        values.update(overrides)
        return self.policy.validate_observation(**values)

    def test_exact_allowlisted_host_is_normalized(self) -> None:
        item = self.observation()
        self.assertEqual(item.source_url, "https://www.binance.com/en/support/faq?x=1")
        self.assertEqual(len(item.fingerprint), 64)

    def test_empty_allowlist_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowlisted"):
            OfficialSourcePolicy(frozenset()).validate_url("https://www.binance.com/")

    def test_deceptive_suffix_hostname_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowlisted"):
            self.policy.validate_url("https://www.binance.com.attacker.example/offer")

    def test_subdomain_is_not_implicitly_trusted(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowlisted"):
            self.policy.validate_url("https://api.www.binance.com/offer")

    def test_http_credentials_and_nonstandard_port_are_rejected(self) -> None:
        for url in (
            "http://www.binance.com/offer",
            "https://user:secret@www.binance.com/offer",
            "https://www.binance.com:8443/offer",
            "https://127.0.0.1/offer",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.policy.validate_url(url)

    def test_off_origin_redirect_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cross-origin redirects"):
            self.observation(final_url="https://attacker.example/landing")

    def test_redirect_to_another_allowlisted_host_is_still_cross_origin(self) -> None:
        with self.assertRaisesRegex(ValueError, "cross-origin redirects"):
            self.observation(final_url="https://support.coinbase.com/landing")

    def test_same_origin_redirect_is_accepted(self) -> None:
        item = self.observation(final_url="https://www.binance.com/en/support/faq?ref=canonical")
        self.assertEqual(item.final_url, "https://www.binance.com/en/support/faq?ref=canonical")

    def test_malformed_digest_is_rejected(self) -> None:
        for digest in ("", "A" * 64, "g" * 64, "a" * 63):
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, "SHA-256"):
                self.observation(evidence_sha256=digest)

    def test_bad_or_future_timestamps_are_rejected(self) -> None:
        invalid = (
            {"observed_at_ms": 0},
            {"source_captured_at_ms": -1},
            {"observed_at_ms": 3_000},
            {"source_captured_at_ms": 1_500, "observed_at_ms": 1_000},
            {"observed_at_ms": True},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.observation(**overrides)

    def test_duplicate_evidence_has_stable_fingerprint(self) -> None:
        first = self.observation()
        second = self.observation(source_url="https://www.binance.com/en/support/faq?x=1")
        self.assertEqual(first.fingerprint, second.fingerprint)
        different_capture = self.observation(source_captured_at_ms=901)
        self.assertNotEqual(first.fingerprint, different_capture.fingerprint)


if __name__ == "__main__":
    unittest.main()
