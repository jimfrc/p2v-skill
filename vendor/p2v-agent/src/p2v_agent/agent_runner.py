"""Build and run the AgentScope ReActAgent for a Remotion project."""

from __future__ import annotations

import inspect
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from agentscope.agent import ReActAgent
from agentscope.message import Msg

from .model_factory import ModelConfig, create_model_and_formatter
from .prompts import SYSTEM_PROMPT, wrap_user_prompt
from .skills import Skill, register_skills
from .tools import build_toolkit


@dataclass
class AgentRunResult:
    reply_text: str
    skills: list[Skill]
    elapsed_seconds: float
    event_log_path: Path


def _skill_roots(project_dir: Path) -> list[Path]:
    """Return the directory roots that may contain agent skills."""

    roots = [
        project_dir / ".claude" / "skills",
        project_dir / "skills",
    ]

    extra = os.environ.get("P2V_EXTRA_SKILLS_DIRS", "")
    for item in extra.split(os.pathsep):
        item = item.strip()
        if item:
            roots.append(Path(item).expanduser())
    return roots


def _make_event_logger(event_log_path: Path):
    """Create a ``post_print`` hook that appends final messages as JSONL.

    AgentScope calls instance hooks with ``(agent, kwargs, output)``.  We only
    log messages where ``last`` is true, because streaming partial chunks would
    otherwise flood the log.
    """

    lock = threading.Lock()

    def _post_print_hook(agent, kwargs, output):  # noqa: ANN001
        message = kwargs.get("msg")
        is_last = kwargs.get("last", True)
        if message is None or not is_last:
            return None

        try:
            payload = message.to_dict()
        except Exception:  # pragma: no cover - defensive
            payload = {
                "name": getattr(message, "name", "unknown"),
                "content": str(getattr(message, "content", "")),
            }

        record = {
            "type": "message",
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "message": payload,
        }
        line = json.dumps(record, ensure_ascii=False, default=str)

        with lock:
            with open(event_log_path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")

        return None

    return _post_print_hook


async def _close_model_client(model) -> None:
    """Close the underlying SDK client, if it has one.

    Without this, httpx prints a noisy "Event loop is closed" traceback when
    the interpreter shuts down.
    """

    client = getattr(model, "client", None)
    closer = getattr(client, "close", None)
    if closer is None:
        return
    try:
        result = closer()
        if inspect.isawaitable(result):
            await result
    except Exception:  # pragma: no cover - best-effort cleanup
        pass


def _append_event(event_log_path: Path, event: dict) -> None:
    record = {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        **event,
    }
    with open(event_log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


async def run_agent(
    project_dir: Path,
    user_prompt: str,
    model_config: ModelConfig,
    max_iters: int,
    event_log_path: Path,
    extra_skill_roots: Optional[Sequence[Path]] = None,
) -> AgentRunResult:
    """Run the agent against ``project_dir`` until it finishes the video."""

    project_dir = Path(project_dir).resolve()
    event_log_path = Path(event_log_path).resolve()
    event_log_path.parent.mkdir(parents=True, exist_ok=True)
    event_log_path.write_text("", encoding="utf-8")

    previous_cwd = Path.cwd()
    started = time.monotonic()
    skills: list[Skill] = []
    model = None

    try:
        os.chdir(project_dir)

        toolkit = build_toolkit(project_dir)

        roots = _skill_roots(project_dir)
        if extra_skill_roots:
            roots.extend(Path(root).expanduser() for root in extra_skill_roots)
        skills = register_skills(toolkit, roots)

        print(f"[agent] {model_config.describe()}")
        print(f"[agent] Registered {len(skills)} skill(s):")
        for skill in skills:
            print(f"        - {skill.name}: {skill.description[:90]}")

        if not any(skill.name == "prompt2video" for skill in skills):
            print(
                "[agent] WARNING: the prompt2video skill was not found in the "
                "project. The agent may not follow the expected workflow."
            )

        model, formatter = create_model_and_formatter(model_config)

        agent = ReActAgent(
            name="p2v-agent",
            sys_prompt=SYSTEM_PROMPT.format(project_dir=str(project_dir)),
            model=model,
            formatter=formatter,
            toolkit=toolkit,
            max_iters=max_iters,
            parallel_tool_calls=False,
        )

        agent.register_instance_hook(
            "post_print",
            "jsonl_event_log",
            _make_event_logger(event_log_path),
        )

        prompt = wrap_user_prompt(user_prompt)
        _append_event(
            event_log_path,
            {
                "type": "run_start",
                "project_dir": str(project_dir),
                "model": model_config.describe(),
                "skills": [skill.name for skill in skills],
                "prompt": prompt,
            },
        )

        print("\n[agent] Starting p2v-agent. This can take several minutes.\n")
        reply = await agent(Msg("p2v-agent-user", prompt, role="user"))

        reply_text = reply.get_text_content() or ""
        elapsed = time.monotonic() - started

        _append_event(
            event_log_path,
            {
                "type": "run_end",
                "elapsed_seconds": round(elapsed, 2),
                "reply": reply_text,
            },
        )

        return AgentRunResult(
            reply_text=reply_text,
            skills=skills,
            elapsed_seconds=elapsed,
            event_log_path=event_log_path,
        )

    finally:
        if model is not None:
            await _close_model_client(model)
        os.chdir(previous_cwd)
