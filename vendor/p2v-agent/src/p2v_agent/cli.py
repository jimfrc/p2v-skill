"""Command-line interface for p2v-agent."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .build import BuildOptions, build_sync
from .errors import P2VAgentError
from .install import run_install


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="p2v-agent",
        description=(
            "Scaffold a Remotion project and run an AgentScope agent to "
            "generate a narrated AI video from a prompt."
        ),
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"p2v-agent {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build",
        help="Scaffold the Remotion project, install skills, and run the agent.",
        description=(
            "Scaffold a Remotion project, install the official Remotion "
            "skills plus the bundled prompt2video skill, then let the "
            "AgentScope agent render the video."
        ),
    )
    build.add_argument(
        "-t",
        "--tmp-dir",
        default=tempfile.gettempdir(),
        help="Parent directory for the generated project (default: OS temp).",
    )
    build.add_argument(
        "-o",
        "--output-dir",
        default="./outputs",
        help="Output directory for the generated video/PDF/log (default: ./outputs).",
    )
    build.add_argument(
        "-f",
        "--prompt-file",
        help="Read the prompt from a UTF-8 file instead of stdin.",
    )
    build.add_argument(
        "--project-dir",
        help="Reuse an existing Remotion project instead of scaffolding one.",
    )
    build.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Scaffold the project, install skills, and print the registered "
            "skills/tools without calling the model."
        ),
    )

    model = build.add_argument_group("model")
    model.add_argument(
        "--provider",
        help="Model provider: anthropic, openai, deepseek, or dashscope.",
    )
    model.add_argument("--model", help="Model name (overrides P2V_MODEL).")
    model.add_argument(
        "--base-url",
        help="API base URL for OpenAI/Anthropic-compatible endpoints.",
    )
    model.add_argument(
        "--api-key",
        help=(
            "API key. Prefer the provider's environment variable instead of "
            "passing secrets on the command line."
        ),
    )
    model.add_argument(
        "--max-tokens",
        type=int,
        default=8192,
        help="Maximum output tokens per model call (default: 8192).",
    )
    model.add_argument(
        "--max-iters",
        type=int,
        default=200,
        help="Maximum agent reasoning/acting iterations (default: 200).",
    )
    model.add_argument(
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Stream model output. Defaults to off for DeepSeek because of an "
            "AgentScope 1.0.21 streaming parser bug; on for other providers. "
            "Override with P2V_STREAM=1/0."
        ),
    )

    install = subparsers.add_parser(
        "install",
        help="Install all bundled skills into <agents-folder>/skills/.",
    )
    install.add_argument(
        "agents_folder",
        nargs="?",
        default=".",
        help="Agent folder that receives a skills/ directory (default: .).",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    # Keep our log lines ordered with the subprocess output (npm/npx) even
    # when stdout is piped.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:  # pragma: no cover - exotic stdout objects
        pass

    try:
        if args.command == "install":
            run_install(args.agents_folder)
            return 0

        options = BuildOptions(
            tmp_dir=Path(args.tmp_dir).expanduser().resolve(),
            output_dir=Path(args.output_dir).expanduser().resolve(),
            prompt_file=args.prompt_file,
            project_dir=Path(args.project_dir) if args.project_dir else None,
            dry_run=args.dry_run,
            provider=args.provider,
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            max_tokens=args.max_tokens,
            max_iters=args.max_iters,
            stream=args.stream,
        )
        artifacts = build_sync(options)
        if artifacts:
            print("\nDone! Artifacts:")
            for artifact in artifacts:
                print(f"  - {artifact}")
        else:
            print("\nDone.")
        return 0

    except P2VAgentError as exc:
        print(f"p2v-agent error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\np2v-agent: interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
