"""Model and formatter selection for the AgentScope agent.

p2v-agent defaults to **DeepSeek's official API** (OpenAI-compatible).  Other
providers remain available via ``--provider``:

- ``deepseek`` (default): ``https://api.deepseek.com`` with ``deepseek-chat``.
- ``openai``: OpenAI and OpenAI-compatible endpoints.
- ``anthropic``: Anthropic's API or an Anthropic-compatible proxy.
- ``dashscope``: Alibaba Cloud DashScope / Qwen.

Configuration can come from CLI flags or environment variables.  The
``P2V_*`` variables take precedence over provider-specific ones.  A project
``.env`` file is loaded by :mod:`p2v_agent.env`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .errors import ConfigError

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5-5",
    "openai": "gpt-4o",
    "deepseek": "deepseek-chat",
    "dashscope": "qwen-max",
}

PROVIDER_ALIASES = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "openai": "openai",
    "gpt": "openai",
    "deepseek": "deepseek",
    "dashscope": "dashscope",
    "qwen": "dashscope",
    "aliyun": "dashscope",
}


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model_name: str
    api_key: Optional[str] = None
    auth_token: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 8192
    stream: bool = True

    def describe(self) -> str:
        """Return a human-readable summary that never contains secrets."""

        bits = [
            f"provider={self.provider}",
            f"model={self.model_name}",
            f"stream={str(self.stream).lower()}",
        ]
        if self.base_url:
            bits.append(f"base_url={self.base_url}")
        if self.api_key:
            bits.append("api_key=***")
        elif self.auth_token:
            bits.append("auth_token=***")
        return " ".join(bits)


def _normalize_provider(value: str) -> str:
    provider = PROVIDER_ALIASES.get(value.strip().lower())
    if provider is None:
        allowed = ", ".join(sorted(set(PROVIDER_ALIASES.values())))
        raise ConfigError(
            f"Unknown model provider {value!r}. Choose one of: {allowed}."
        )
    return provider


def _detect_provider() -> str:
    explicit = os.environ.get("P2V_PROVIDER", "").strip()
    if explicit:
        return _normalize_provider(explicit)

    # DeepSeek is the default backend for p2v-agent.
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    if os.environ.get("P2V_API_KEY"):
        return "deepseek"
    if os.environ.get("DASHSCOPE_API_KEY"):
        return "dashscope"
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
        "ANTHROPIC_AUTH_TOKEN"
    ):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    # Let the caller report a helpful missing-credential error below.
    return "deepseek"


def resolve_model_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 8192,
    stream: Optional[bool] = None,
) -> ModelConfig:
    """Resolve CLI flags and environment variables into a ModelConfig."""

    provider_name = (
        _normalize_provider(provider) if provider else _detect_provider()
    )

    if stream is None:
        env_stream = os.environ.get("P2V_STREAM", "").strip().lower()
        if env_stream in {"1", "true", "yes", "on"}:
            stream = True
        elif env_stream in {"0", "false", "no", "off"}:
            stream = False
        else:
            # AgentScope 1.0.21's OpenAI streaming parser crashes when a
            # provider (DeepSeek) sends `"audio": null` in a delta.  The
            # non-streaming path is unaffected, so disable streaming for
            # DeepSeek unless the user explicitly enables it.
            stream = provider_name != "deepseek"

    model_name = (
        model
        or os.environ.get("P2V_MODEL")
        or os.environ.get(f"{provider_name.upper()}_MODEL")
        or DEFAULT_MODELS[provider_name]
    )

    key = api_key or os.environ.get("P2V_API_KEY")
    token: Optional[str] = None
    url = base_url or os.environ.get("P2V_BASE_URL")

    if provider_name == "anthropic":
        key = key or os.environ.get("ANTHROPIC_API_KEY")
        token = os.environ.get("P2V_AUTH_TOKEN") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN"
        )
        if key:
            # An explicit API key wins over the ambient auth token.
            token = None
        url = url or os.environ.get("ANTHROPIC_BASE_URL")
        if not key and not token:
            raise ConfigError(
                "No Anthropic credentials found. Set ANTHROPIC_API_KEY, "
                "ANTHROPIC_AUTH_TOKEN, or P2V_API_KEY (and optionally "
                "P2V_BASE_URL)."
            )

    elif provider_name == "deepseek":
        key = (
            key
            or os.environ.get("DEEPSEEK_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        url = (
            url
            or os.environ.get("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com"
        )
        if not key:
            raise ConfigError(
                "No DeepSeek API key found. Set DEEPSEEK_API_KEY or "
                "P2V_API_KEY."
            )

    elif provider_name == "dashscope":
        key = key or os.environ.get("DASHSCOPE_API_KEY")
        if not key:
            raise ConfigError(
                "No DashScope API key found. Set DASHSCOPE_API_KEY or "
                "P2V_API_KEY."
            )

    elif provider_name == "openai":
        key = key or os.environ.get("OPENAI_API_KEY")
        url = url or os.environ.get("OPENAI_BASE_URL")
        if not key:
            raise ConfigError(
                "No OpenAI API key found. Set OPENAI_API_KEY or P2V_API_KEY, "
                "or choose another provider with --provider."
            )

    return ModelConfig(
        provider=provider_name,
        model_name=model_name,
        api_key=key,
        auth_token=token,
        base_url=url,
        max_tokens=max_tokens,
        stream=stream,
    )


def create_model_and_formatter(config: ModelConfig):
    """Instantiate the AgentScope chat model and matching formatter."""

    provider = config.provider

    if provider == "anthropic":
        from agentscope.formatter import AnthropicChatFormatter
        from agentscope.model import AnthropicChatModel

        client_kwargs: dict = {}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url
        if config.auth_token:
            client_kwargs["auth_token"] = config.auth_token

        model = AnthropicChatModel(
            model_name=config.model_name,
            api_key=config.api_key,
            max_tokens=config.max_tokens,
            stream=config.stream,
            client_kwargs=client_kwargs or None,
        )
        formatter = AnthropicChatFormatter()

    elif provider == "dashscope":
        from agentscope.formatter import DashScopeChatFormatter
        from agentscope.model import DashScopeChatModel

        model = DashScopeChatModel(
            model_name=config.model_name,
            api_key=config.api_key,
            stream=config.stream,
        )
        formatter = DashScopeChatFormatter()

    elif provider == "deepseek":
        from agentscope.formatter import DeepSeekChatFormatter
        from agentscope.model import OpenAIChatModel

        client_kwargs = {}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url
        model = OpenAIChatModel(
            model_name=config.model_name,
            api_key=config.api_key,
            stream=config.stream,
            client_kwargs=client_kwargs or None,
        )
        formatter = DeepSeekChatFormatter()

    else:  # openai
        from agentscope.formatter import OpenAIChatFormatter
        from agentscope.model import OpenAIChatModel

        client_kwargs = {}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url
        model = OpenAIChatModel(
            model_name=config.model_name,
            api_key=config.api_key,
            stream=config.stream,
            client_kwargs=client_kwargs or None,
        )
        formatter = OpenAIChatFormatter()

    return model, formatter
