"""Exceptions shared by the p2v-agent CLI."""

from __future__ import annotations


class P2VAgentError(RuntimeError):
    """Base error for expected, user-facing failures."""


class ConfigError(P2VAgentError):
    """Raised when the model or runtime configuration is invalid."""


class BuildError(P2VAgentError):
    """Raised when scaffolding or a required external command fails."""
