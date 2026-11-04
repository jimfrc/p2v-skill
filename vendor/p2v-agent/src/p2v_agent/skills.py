"""Discovery, registration and installation of agent skills.

AgentScope implements Anthropic-style agent skills.  A skill is a directory
with a top-level ``SKILL.md`` file whose YAML front matter declares ``name``
and ``description``.  ``Toolkit.register_agent_skill`` adds its metadata to the
agent's system prompt; the agent then reads the ``SKILL.md`` file on demand
with the ``Read`` tool.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import frontmatter

from .errors import P2VAgentError


@dataclass(frozen=True)
class Skill:
    """Metadata for one discovered skill."""

    name: str
    description: str
    directory: Path

    @property
    def skill_md(self) -> Path:
        return self.directory / "SKILL.md"


def read_skill_metadata(skill_dir: Path) -> Skill:
    """Read and validate the YAML front matter of ``<skill_dir>/SKILL.md``."""

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise P2VAgentError(f"Skill at {skill_dir} has no SKILL.md file.")

    try:
        post = frontmatter.load(str(skill_md))
    except Exception as exc:  # pragma: no cover - malformed user skills
        raise P2VAgentError(f"Could not parse {skill_md}: {exc}") from exc

    name = post.get("name")
    description = post.get("description")
    if not name or not description:
        raise P2VAgentError(
            f"{skill_md} must have YAML front matter with `name` and "
            "`description` fields."
        )

    return Skill(
        name=str(name).strip(),
        description=str(description).strip(),
        directory=skill_dir.resolve(),
    )


def discover_skill_dirs(roots: Iterable[Path]) -> list[Path]:
    """Find skill directories under each root.

    A root may itself be a skill directory, or it may contain skill
    subdirectories (the layout produced by ``npx skills add`` under
    ``.claude/skills``).  Results are deduplicated by resolved path and sorted
    by name for deterministic prompts.
    """

    found: dict[Path, Path] = {}
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        if (root / "SKILL.md").is_file():
            found[root.resolve()] = root.resolve()
            continue
        for child in root.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                found[child.resolve()] = child.resolve()

    return sorted(found.values(), key=lambda path: path.name.lower())


def list_skills(roots: Iterable[Path]) -> list[Skill]:
    """Discover and parse every skill under ``roots``.

    Invalid or unrelated directories are skipped so one malformed skill does
    not abort the whole build.
    """

    skills: list[Skill] = []
    seen_names: set[str] = set()
    for skill_dir in discover_skill_dirs(roots):
        try:
            skill = read_skill_metadata(skill_dir)
        except P2VAgentError:
            continue
        if skill.name in seen_names:
            continue
        seen_names.add(skill.name)
        skills.append(skill)
    return skills


def register_skills(toolkit, roots: Sequence[Path]) -> list[Skill]:
    """Register every discovered skill on an AgentScope ``Toolkit``.

    Returns the skills that were successfully registered.  Duplicate names are
    skipped with a warning, because AgentScope rejects duplicate skill names.
    """

    registered: list[Skill] = []
    seen_names: set[str] = set()

    for skill in list_skills(roots):
        if skill.name in seen_names:
            print(f"[skills] Skipping duplicate skill name: {skill.name}")
            continue
        try:
            toolkit.register_agent_skill(str(skill.directory))
        except ValueError as exc:
            print(f"[skills] Could not register {skill.name}: {exc}")
            continue
        seen_names.add(skill.name)
        registered.append(skill)

    return registered


def copy_prompt2video_skill(source: Path, project_dir: Path) -> Path:
    """Copy the bundled prompt2video skill into a generated project.

    It is placed at ``<project>/.claude/skills/prompt2video`` so the relative
    paths inside ``SKILL.md`` (``scripts/tts.ps1``, ``scripts/*.mjs``) keep
    working exactly as they did with Claude Code.
    """

    source = Path(source)
    if not (source / "SKILL.md").is_file():
        raise P2VAgentError(f"Bundled skill is missing SKILL.md: {source}")

    destination = Path(project_dir) / ".claude" / "skills" / "prompt2video"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)
    return destination


def copy_skill_dirs(
    skill_dirs: Iterable[Path], target_skills_dir: Path
) -> list[Path]:
    """Copy each skill directory into ``target_skills_dir``, overwriting."""

    target_skills_dir = Path(target_skills_dir)
    target_skills_dir.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for skill_dir in skill_dirs:
        skill_dir = Path(skill_dir)
        target_dir = target_skills_dir / skill_dir.name
        shutil.copytree(skill_dir, target_dir, dirs_exist_ok=True)
        copied.append(target_dir)

    return copied


def install_bundled_skills(source_skills_dir: Path, agents_folder: Path) -> list[Path]:
    """Copy every bundled skill folder into ``<agents_folder>/skills``.

    Mirrors the original ``prompt2video install`` command.
    """

    source_skills_dir = Path(source_skills_dir)
    target_skills_dir = Path(agents_folder) / "skills"

    if not source_skills_dir.is_dir():
        raise P2VAgentError(f"Skills folder not found: {source_skills_dir}")

    skill_dirs = [
        entry
        for entry in sorted(source_skills_dir.iterdir())
        if entry.is_dir() and (entry / "SKILL.md").is_file()
    ]
    if not skill_dirs:
        raise P2VAgentError(f"No skills found in {source_skills_dir}")

    return copy_skill_dirs(skill_dirs, target_skills_dir)
