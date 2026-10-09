"""Tests for the dependency-free LLM provider adapter."""
import json
import os
import unittest
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


if __name__ == "__main__":
    unittest.main()
