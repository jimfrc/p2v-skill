"""Path helpers for bundled skills and the source checkout.

The canonical copy of the bundled ``prompt2video`` skill lives in the
top-level ``skills/`` folder of the repository (as requested for the
``p2v-agent`` project).  When the package is installed as a wheel, the same
files are installed under ``<prefix>/share/p2v-agent/skills`` via
``pyproject.toml``'s ``data-files`` section.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .errors import P2VAgentError

PACKAGE_DIR = Path(__file__).resolve().parent


def repo_root() -> Path:
    """Return the source checkout root (``p2v-agent/``).

    Works for ``src/p2v_agent/paths.py`` during development.  For an installed
    wheel this path will not contain ``skills/`` and the share directory is
    used instead.
    """

    return PACKAGE_DIR.parents[1]


def bundled_skills_dir() -> Path:
    """Locate the directory that contains the bundled skill folders.

    Resolution order:
    1. ``P2V_SKILLS_DIR`` environment variable (explicit override).
    2. ``<repo>/skills`` when running from a source checkout.
    3. ``<sys.prefix>/share/p2v-agent/skills`` for an installed wheel.
    4. ``<package>/_bundled_skills`` for alternative packaged layouts.
    """

    candidates = []

    env_dir = os.environ.get("P2V_SKILLS_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser())

    candidates.append(repo_root() / "skills")
    candidates.append(Path(sys.prefix) / "share" / "p2v-agent" / "skills")
    candidates.append(PACKAGE_DIR / "_bundled_skills")

    for candidate in candidates:
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate.resolve()

    searched = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise P2VAgentError(
        "Could not find the bundled prompt2video skill. Set P2V_SKILLS_DIR "
        "or reinstall p2v-agent. Searched:\n" + searched
    )


def prompt2video_skill_dir() -> Path:
    """Return the bundled ``prompt2video`` skill directory."""

    path = bundled_skills_dir() / "prompt2video"
    if not (path / "SKILL.md").is_file():
        raise P2VAgentError(
            f"Bundled prompt2video skill is incomplete: {path / 'SKILL.md'} "
            "does not exist."
        )
    return path


def bundled_remotion_skill_dirs() -> list[Path]:
    """Return the bundled official Remotion skill directories.

    These are the ``remotion-*`` folders vendored from
    ``remotion-dev/skills``.  An empty list means the bundle is absent (for
    example an older installed wheel), in which case the build falls back to
    fetching the skills from GitHub.
    """

    try:
        root = bundled_skills_dir()
    except P2VAgentError:
        return []

    return sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir()
            and path.name.startswith("remotion-")
            and (path / "SKILL.md").is_file()
        ),
        key=lambda path: path.name.lower(),
    )
