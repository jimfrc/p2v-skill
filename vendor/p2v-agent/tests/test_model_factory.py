from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from p2v_agent.errors import ConfigError
from p2v_agent.model_factory import resolve_model_config


class ModelConfigTests(unittest.TestCase):
    def test_anthropic_auth_token_and_base_url(self) -> None:
        env = {
            "ANTHROPIC_AUTH_TOKEN": "token-123",
            "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic",
            "ANTHROPIC_MODEL": "demo-model",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_model_config()
        self.assertEqual(config.provider, "anthropic")
        self.assertEqual(config.model_name, "demo-model")
        self.assertEqual(config.auth_token, "token-123")
        self.assertIsNone(config.api_key)
        self.assertEqual(
            config.base_url, "https://example.invalid/anthropic"
        )
        self.assertTrue(config.stream)
        self.assertNotIn("token-123", config.describe())

    def test_api_key_wins_over_auth_token(self) -> None:
        env = {
            "ANTHROPIC_API_KEY": "key-123",
            "ANTHROPIC_AUTH_TOKEN": "token-123",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_model_config()
        self.assertEqual(config.api_key, "key-123")
        self.assertIsNone(config.auth_token)

    def test_deepseek_defaults(self) -> None:
        with patch.dict(
            os.environ, {"DEEPSEEK_API_KEY": "ds-key"}, clear=True
        ):
            config = resolve_model_config()
        self.assertEqual(config.provider, "deepseek")
        self.assertEqual(config.model_name, "deepseek-chat")
        self.assertEqual(config.base_url, "https://api.deepseek.com")
        # DeepSeek defaults to non-streaming (AgentScope 1.0.21 parser bug).
        self.assertFalse(config.stream)

    def test_deepseek_stream_can_be_enabled(self) -> None:
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "ds-key", "P2V_STREAM": "1"},
            clear=True,
        ):
            config = resolve_model_config()
        self.assertTrue(config.stream)

    def test_generic_api_key_defaults_to_deepseek(self) -> None:
        with patch.dict(os.environ, {"P2V_API_KEY": "generic"}, clear=True):
            config = resolve_model_config()
        self.assertEqual(config.provider, "deepseek")
        self.assertEqual(config.api_key, "generic")
        self.assertEqual(config.base_url, "https://api.deepseek.com")

    def test_deepseek_model_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "ds-key",
                "DEEPSEEK_MODEL": "deepseek-reasoner",
            },
            clear=True,
        ):
            config = resolve_model_config()
        self.assertEqual(config.model_name, "deepseek-reasoner")

    def test_cli_overrides_env(self) -> None:
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "ds-key", "P2V_MODEL": "env-model"},
            clear=True,
        ):
            config = resolve_model_config(
                model="cli-model",
                base_url="https://cli.invalid",
                max_tokens=1234,
            )
        self.assertEqual(config.model_name, "cli-model")
        self.assertEqual(config.base_url, "https://cli.invalid")
        self.assertEqual(config.max_tokens, 1234)

    def test_missing_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError):
                resolve_model_config(provider="openai")

    def test_unknown_provider(self) -> None:
        with self.assertRaises(ConfigError):
            resolve_model_config(provider="not-a-provider")


if __name__ == "__main__":
    unittest.main()
