"""Load model configuration from ``.env`` files.

The DeepSeek API key and related settings are read from environment
variables.  For convenience, p2v-agent also loads a project ``.env`` file so
users do not have to export variables in every shell.

Precedence is: real environment variables > ``P2V_ENV_FILE`` > ``.env`` found
from the current directory upward > ``<repo>/.env``.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from .paths import repo_root


def _load(path: Path, loaded: list[Path]) -> None:
    if not path.is_file():
        return
    resolved = path.resolve()
    if any(existing == resolved for existing in loaded):
        return
    load_dotenv(resolved, override=False)
    loaded.append(resolved)


def load_env_files() -> list[Path]:
    """Load ``.env`` files and return the paths that were used.

    Existing process environment variables always win (``override=False``).
    """

    loaded: list[Path] = []

    explicit = os.environ.get("P2V_ENV_FILE", "").strip()
    if explicit:
        _load(Path(explicit).expanduser(), loaded)

    found = find_dotenv(usecwd=True)
    if found:
        _load(Path(found), loaded)

    _load(repo_root() / ".env", loaded)

    return loaded
