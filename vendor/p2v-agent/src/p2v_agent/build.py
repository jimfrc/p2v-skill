"""The ``build`` workflow: scaffold, install skills, run the agent, copy out."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .agent_runner import run_agent
from .browser import configure_remotion_browser
from .env import load_env_files
from .errors import BuildError, ConfigError
from .model_factory import resolve_model_config
from .paths import bundled_remotion_skill_dirs, prompt2video_skill_dir
from .skills import copy_prompt2video_skill, copy_skill_dirs, register_skills
from .tools import build_toolkit

REMOTION_SKILLS_REPO = "remotion-dev/skills"


@dataclass
class BuildOptions:
    tmp_dir: Path
    output_dir: Path
    prompt_file: Optional[str] = None
    project_dir: Optional[Path] = None
    dry_run: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_tokens: int = 8192
    max_iters: int = 200
    stream: Optional[bool] = None


def read_prompt(prompt_file: Optional[str]) -> str:
    """Read the user prompt from a UTF-8 file or stdin, stripping a BOM."""

    if prompt_file:
        path = Path(prompt_file).expanduser().resolve()
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise BuildError(f"Could not read prompt file {path}: {exc}") from exc
        return data.decode("utf-8-sig", errors="replace").strip()

    if sys.stdin.isatty():
        return ""

    data = sys.stdin.buffer.read()
    return data.decode("utf-8-sig", errors="replace").strip()


def _timestamp_suffix() -> str:
    return (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"
    )


def _require_node_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise BuildError(
            f"`{name}` was not found on PATH. Install Node.js >= 20.12 "
            "(https://nodejs.org/) and retry."
        )


def _run_checked(args: list[str], cwd: Path, label: str) -> None:
    """Run an external command with inherited stdio and raise on failure."""

    if os.name == "nt":
        command: object = subprocess.list2cmdline(args)
        use_shell = True
    else:
        command = args
        use_shell = False

    print(f"[build] {label}: {' '.join(args)}")
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            shell=use_shell,
            check=False,
        )
    except OSError as exc:
        raise BuildError(f"Could not start {label}: {exc}") from exc

    if completed.returncode != 0:
        raise BuildError(
            f"{label} failed with exit code {completed.returncode}."
        )


def scaffold_project(tmp_dir: Path, project_name: str) -> Path:
    """Create a blank Remotion project and return its directory."""

    _require_node_tool("npx")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"[build] Creating Remotion project in {tmp_dir / project_name}")
    _run_checked(
        [
            "npx",
            "--yes",
            "create-video@latest",
            "--yes",
            "--blank",
            project_name,
        ],
        cwd=tmp_dir,
        label="create-video",
    )

    project_dir = tmp_dir / project_name
    if not (project_dir / "package.json").is_file():
        raise BuildError(
            f"create-video did not produce a package.json in {project_dir}."
        )
    return project_dir


def install_remotion_skills(project_dir: Path) -> Path:
    """Install Remotion's official agent skills into ``.claude/skills``.

    The skills are vendored under the repository's ``skills/remotion-*``
    folders, so the common path copies them locally and needs no network
    access.  If this build has no bundled copy (for example an older installed
    wheel), fall back to ``npx skills add``.

    ``-a claude-code`` selects the Claude Code skill layout; ``--copy`` avoids
    symlink privileges issues on Windows.  The AgentScope agent reads the same
    ``.claude/skills/<name>/SKILL.md`` files.
    """

    skills_dir = project_dir / ".claude" / "skills"
    bundled = bundled_remotion_skill_dirs()

    if bundled:
        print(
            f"[build] Installing {len(bundled)} bundled Remotion skill(s) "
            "from skills/remotion-*"
        )
        copy_skill_dirs(bundled, skills_dir)
    else:
        _require_node_tool("npx")
        print("[build] Installing official Remotion skills (remotion-dev/skills)")
        try:
            _run_checked(
                [
                    "npx",
                    "--yes",
                    "skills",
                    "add",
                    REMOTION_SKILLS_REPO,
                    "-a",
                    "claude-code",
                    "--yes",
                    "--copy",
                ],
                cwd=project_dir,
                label="skills add remotion-dev/skills",
            )
        except BuildError as exc:
            raise BuildError(
                f"{exc} The skills CLI clones {REMOTION_SKILLS_REPO} from "
                "GitHub; check network access to github.com and retry."
            ) from exc

    if not skills_dir.is_dir() or not any(skills_dir.glob("*/SKILL.md")):
        raise BuildError(
            "Remotion skills were not installed into "
            f"{skills_dir} (expected */SKILL.md)."
        )
    return skills_dir


def copy_bundled_skill(project_dir: Path) -> Path:
    """Copy the bundled prompt2video skill into the project's skill folder."""

    print("[build] Copying bundled prompt2video skill")
    return copy_prompt2video_skill(
        prompt2video_skill_dir(),
        project_dir,
    )


def _copy_artifacts(
    project_dir: Path,
    output_dir: Path,
    project_name: str,
    event_log_name: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = [
        (project_dir / "out" / "video.mp4", f"{project_name}_video.mp4"),
        (project_dir / "out" / "slides.pdf", f"{project_name}_slides.pdf"),
        (
            project_dir / "out" / event_log_name,
            f"{project_name}_{event_log_name}",
        ),
    ]

    copied: list[Path] = []
    for source, filename in artifacts:
        if not source.is_file():
            print(f"[build] WARNING: missing artifact: {source}")
            continue
        destination = output_dir / filename
        shutil.copy2(source, destination)
        print(f"[build] Copied {source} -> {destination}")
        copied.append(destination)

    return copied


def _dry_run(
    project_dir: Path,
    event_log_path: Path,
) -> None:
    """Validate the generated project and skill registration without an LLM."""

    previous_cwd = Path.cwd()
    try:
        os.chdir(project_dir)
        toolkit = build_toolkit(project_dir)
        roots = [
            project_dir / ".claude" / "skills",
            project_dir / "skills",
        ]
        skills = register_skills(toolkit, roots)
        print(f"[dry-run] Working directory: {project_dir}")
        print(f"[dry-run] Event log would be: {event_log_path}")
        print(f"[dry-run] Registered {len(skills)} skill(s):")
        for skill in skills:
            print(f"          - {skill.name}: {skill.description}")
        print("[dry-run] Tool schemas:")
        for name in sorted(toolkit.tools):
            print(f"          - {name}")
        if not any(skill.name == "prompt2video" for skill in skills):
            raise BuildError(
                "The prompt2video skill was not registered; check the "
                "bundled skills folder."
            )
    finally:
        os.chdir(previous_cwd)


async def run_build(options: BuildOptions) -> list[Path]:
    """Execute the full build pipeline and return copied artifact paths."""

    loaded_env_files = load_env_files()
    if loaded_env_files:
        print(
            "[build] Loaded environment from: "
            + ", ".join(str(path) for path in loaded_env_files)
        )

    user_prompt = read_prompt(options.prompt_file)
    if not user_prompt:
        raise BuildError(
            "No user prompt provided. Use --prompt-file prompt.txt or pipe "
            "text on stdin."
        )

    # Resolve model configuration early so we fail before spending time on
    # scaffolding when credentials are missing.
    model_config = None
    if not options.dry_run:
        try:
            model_config = resolve_model_config(
                provider=options.provider,
                model=options.model,
                base_url=options.base_url,
                api_key=options.api_key,
                max_tokens=options.max_tokens,
                stream=options.stream,
            )
        except ConfigError as exc:
            raise ConfigError(
                f"{exc}\nTip: run with --dry-run to scaffold the project and "
                "inspect skills without calling a model."
            ) from exc

    if options.project_dir is not None:
        project_dir = Path(options.project_dir).expanduser().resolve()
        if not project_dir.is_dir():
            raise BuildError(f"Project directory not found: {project_dir}")
        project_name = project_dir.name
        print(f"[build] Reusing existing project: {project_dir}")
    else:
        project_name = f"p2v_agent_{_timestamp_suffix()}"
        project_dir = scaffold_project(options.tmp_dir, project_name)

    install_remotion_skills(project_dir)
    copy_bundled_skill(project_dir)
    configure_remotion_browser(project_dir)

    out_dir = project_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    event_log_name = "video.agent_events.jsonl"
    event_log_path = out_dir / event_log_name

    if options.dry_run:
        _dry_run(project_dir, event_log_path)
        print("[dry-run] Skipping the agent run.")
        return []

    assert model_config is not None

    try:
        result = await run_agent(
            project_dir=project_dir,
            user_prompt=user_prompt,
            model_config=model_config,
            max_iters=options.max_iters,
            event_log_path=event_log_path,
        )
    except KeyboardInterrupt:
        raise BuildError("Interrupted by the user.") from None

    print(
        f"\n[build] Agent finished in {result.elapsed_seconds:.1f}s. "
        f"Registered skills: {len(result.skills)}"
    )
    if result.reply_text:
        print(f"[build] Agent summary:\n{result.reply_text}\n")

    copied = _copy_artifacts(
        project_dir, options.output_dir, project_name, event_log_name
    )

    if not any(path.name.endswith("_video.mp4") for path in copied) and not any(
        path.name.endswith("_slides.pdf") for path in copied
    ):
        raise BuildError(
            "The agent finished but neither out/video.mp4 nor out/slides.pdf "
            f"was produced. See the event log: {event_log_path}"
        )

    return copied


def build_sync(options: BuildOptions) -> list[Path]:
    """Synchronous wrapper used by the CLI and tests."""

    return asyncio.run(run_build(options))


__all__ = [
    "BuildOptions",
    "build_sync",
    "copy_bundled_skill",
    "install_remotion_skills",
    "read_prompt",
    "run_build",
    "scaffold_project",
]
