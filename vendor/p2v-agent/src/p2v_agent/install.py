"""The ``install`` command: copy bundled skills into an agent folder."""

from __future__ import annotations

from pathlib import Path

from .paths import bundled_skills_dir
from .skills import install_bundled_skills


def run_install(agents_folder: str) -> list[Path]:
    """Install all bundled skills into ``<agents_folder>/skills``."""

    target = Path(agents_folder).expanduser().resolve()
    installed = install_bundled_skills(bundled_skills_dir(), target)
    for path in installed:
        print(f"Installed {path.name} skill at {path}")
    return installed
