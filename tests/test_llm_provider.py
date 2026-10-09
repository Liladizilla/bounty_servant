"""Tests for the dependency-free LLM provider adapter."""
import io
import json
import os
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

import llm_provider


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class UnreadableBody:
    def read(self):
        raise OSError("body unavailable")


def http_error(body=b'{"error":{"message":"request failed"}}', code=429):
    return HTTPError(
        "https://provider.invalid/generate",
        code,
        "provider error",
        {},
        io.BytesIO(body),
    )


class ProviderTests(unittest.TestCase):
    def test_rejects_empty_prompt(self):
        with self.assertRaises(ValueError):
            llm_provider.generate_text("  ")

    def test_rejects_invalid_token_limit(self):
        with self.assertRaises(ValueError):
            llm_provider.generate_text("hello", max_output_tokens=0)

    def test_requires_configured_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(llm_provider.ProviderError):
                llm_provider.generate_text("hello")

    def test_gemini_request_returns_text(self):
        payload = {"candidates": [{"content": {"parts": [{"text": "patch plan"}]}}]}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            with patch("llm_provider.urlopen", return_value=FakeResponse(payload)) as mocked:
                result = llm_provider.generate_text("inspect issue", system="Be precise")
        self.assertEqual(result, "patch plan")
        request = mocked.call_args.args[0]
        self.assertIn("generateContent", request.full_url)
        self.assertNotIn("test-key", request.headers.get("Authorization", ""))

    def test_gemini_legacy_secret_name_returns_text(self):
        payload = {"candidates": [{"content": {"parts": [{"text": "alias works"}]}}]}
        with patch.dict(os.environ, {"GEMINI": "test-key"}, clear=True):
            with patch("llm_provider.urlopen", return_value=FakeResponse(payload)):
                result = llm_provider.generate_text("inspect issue")
        self.assertEqual(result, "alias works")

    def test_groq_request_returns_text(self):
        payload = {"choices": [{"message": {"content": "review plan"}}]}
        env = {"GROQ_API_KEY": "test-key", "BOUNTY_LLM_PROVIDER": "groq"}
        with patch.dict(os.environ, env, clear=True):
            with patch("llm_provider.urlopen", return_value=FakeResponse(payload)) as mocked:
                result = llm_provider.generate_text("inspect issue")
        self.assertEqual(result, "review plan")
        request = mocked.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer test-key")

    def test_http_error_includes_status_and_json_message(self):
        error = http_error(b'{"error":{"message":"invalid model"}}', code=400)
        description = llm_provider._http_error_description(error)
        self.assertIn("HTTP 400", description)
        self.assertIn("invalid model", description)

    def test_http_error_includes_plain_text_body(self):
        description = llm_provider._http_error_description(
            http_error(b"provider is temporarily unavailable", code=503)
        )
        self.assertIn("HTTP 503", description)
        self.assertIn("temporarily unavailable", description)

    def test_http_error_redacts_all_supported_secret_names(self):
        for name in ("GEMINI_API_KEY", "GEMINI", "GROQ_API_KEY"):
            with self.subTest(secret_name=name):
                secret = "never-log-this-secret"
                with patch.dict(os.environ, {name: secret}, clear=True):
                    error = http_error(
                        json.dumps({"error": {"message": f"bad credential {secret}"}}).encode()
                    )
                    description = llm_provider._http_error_description(error)
                self.assertNotIn(secret, description)
                self.assertIn("[REDACTED]", description)

    def test_http_error_handles_unreadable_body(self):
        error = HTTPError(
            "https://provider.invalid/generate",
            502,
            "provider error",
            {},
            UnreadableBody(),
        )
        description = llm_provider._http_error_description(error)
        self.assertIn("HTTP 502", description)

    def test_auto_mode_falls_back_from_gemini_http_error_to_groq(self):
        groq_payload = {"choices": [{"message": {"content": "fallback worked"}}]}
        env = {
            "GEMINI_API_KEY": "gemini-test-key",
            "GROQ_API_KEY": "groq-test-key",
            "BOUNTY_LLM_PROVIDER": "auto",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch(
                "llm_provider.urlopen",
                side_effect=[
                    http_error(b'{"error":{"message":"quota exceeded"}}', code=429),
                    FakeResponse(groq_payload),
                ],
            ) as mocked:
                result = llm_provider.generate_text("inspect issue")
        self.assertEqual(result, "fallback worked")
        self.assertEqual(mocked.call_count, 2)


if __name__ == "__main__":
    unittest.main()
