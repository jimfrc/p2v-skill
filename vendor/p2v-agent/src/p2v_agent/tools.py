"""Coding tools for the AgentScope agent.

The tool names intentionally mirror Claude Code's tools (``Bash``, ``Read``,
``Write``, ``Edit``, ``Glob``, ``Grep``, ``WebFetch``) because the bundled
skills refer to them by name (for example "use the Write tool").
"""

from __future__ import annotations

import asyncio
import fnmatch
import glob as glob_module
import html
import locale
import os
import re
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Optional

from agentscope.message import TextBlock
from agentscope.tool import Toolkit, ToolResponse

MAX_OUTPUT_CHARS = 30_000
MAX_READ_LINES = 2_000
MAX_GREP_RESULTS = 200
SKIPPED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
    "dist",
    "build",
}


def _text(message: str) -> ToolResponse:
    return ToolResponse(content=[TextBlock(type="text", text=message)])


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    half = max(limit // 2, 1)
    omitted = len(text) - limit
    return (
        text[:half]
        + f"\n... [{omitted} characters truncated] ...\n"
        + text[-half:]
    )


def _decode(data: bytes) -> str:
    """Decode subprocess output, falling back to the platform code page.

    A Windows ``cmd.exe`` often emits GBK/CP936 for localized tools; a strict
    UTF-8 decode would raise and lose the tool result.
    """

    if not data:
        return ""
    encodings = ["utf-8", locale.getpreferredencoding(False), "gbk", "latin-1"]
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _resolve(workdir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workdir / path
    return path.resolve()


def _ensure_inside(workdir: Path, path: Path) -> None:
    try:
        path.relative_to(workdir)
    except ValueError as exc:
        raise ValueError(
            f"Refusing to write outside the project directory: {path}"
        ) from exc


def _format_shell_result(
    returncode: int,
    stdout: str,
    stderr: str,
    timed_out: bool = False,
    timeout: Optional[int] = None,
) -> str:
    if timed_out:
        stderr = (
            stderr
            + f"\nTimeoutError: command exceeded the {timeout}s timeout and "
            "was terminated."
        )
    return (
        f"<returncode>{returncode}</returncode>\n"
        f"<stdout>{_truncate(stdout)}</stdout>\n"
        f"<stderr>{_truncate(stderr)}</stderr>"
    )


def _run_shell_sync(command: str, cwd: str, timeout: int) -> str:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    # Reduce noisy ANSI/interactive output from npm/npx.
    env.setdefault("CI", "1")
    env.setdefault("NO_COLOR", "1")

    popen_kwargs: dict = {
        "cwd": cwd,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "env": env,
    }

    if os.name == "nt":
        # subprocess with shell=True uses cmd.exe and resolves npx.cmd /
        # powershell.exe through PATHEXT.
        process = subprocess.Popen(command, shell=True, **popen_kwargs)
    else:
        bash = shutil.which("bash")
        if bash:
            process = subprocess.Popen(
                [bash, "-lc", command],
                start_new_session=True,
                **popen_kwargs,
            )
        else:
            process = subprocess.Popen(
                command,
                shell=True,
                start_new_session=True,
                **popen_kwargs,
            )

    timed_out = False
    try:
        stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - stubborn child
            process.kill()
            stdout_bytes, stderr_bytes = process.communicate()

    return _format_shell_result(
        process.returncode if process.returncode is not None else -1,
        _decode(stdout_bytes),
        _decode(stderr_bytes),
        timed_out=timed_out,
        timeout=timeout,
    )


async def Bash(command: str, timeout: int = 600) -> ToolResponse:
    """Execute a shell command and return its return code, stdout and stderr.

    Use this for any command-line work: npx, npm, node, powershell, ffmpeg,
    ffprobe, etc. The command runs inside the project directory.

    Args:
        command (str):
            The shell command to execute. On Windows it is passed to cmd.exe;
            on macOS/Linux it is passed to bash.
        timeout (int):
            Maximum number of seconds to wait. Defaults to 600. Rendering can
            take longer, so pass a larger value (up to 3600) for
            `npx remotion render`.
    """
    timeout = max(1, min(int(timeout), 3600))
    cwd = os.getcwd()
    output = await asyncio.to_thread(_run_shell_sync, command, cwd, timeout)
    return _text(output)


async def Read(
    file_path: str,
    offset: int = 1,
    limit: int = MAX_READ_LINES,
) -> ToolResponse:
    """Read a text file and return its contents with line numbers.

    Args:
        file_path (str):
            Path to the file, absolute or relative to the project directory.
        offset (int):
            First line to return, 1-based. Defaults to 1.
        limit (int):
            Maximum number of lines to return. Defaults to 2000.
    """
    path = _resolve(Path.cwd(), file_path)
    if not path.is_file():
        return _text(f"Error: file not found: {path}")

    try:
        data = path.read_bytes()
    except OSError as exc:
        return _text(f"Error: could not read {path}: {exc}")

    if b"\x00" in data[:8192]:
        return _text(
            f"Error: {path} appears to be a binary file "
            f"({len(data)} bytes); not showing its contents."
        )

    text = _decode(data)
    lines = text.splitlines()
    if not lines:
        return _text(f"(empty file: {path})")

    offset = max(1, int(offset))
    limit = max(1, min(int(limit), 10_000))
    start = offset - 1
    selected = lines[start : start + limit]
    if not selected:
        return _text(
            f"(no lines at offset {offset}; file has {len(lines)} lines)"
        )

    numbered = "\n".join(
        f"{line_number:>6}\t{line}"
        for line_number, line in enumerate(selected, start=start + 1)
    )
    remaining = len(lines) - (start + len(selected))
    suffix = (
        f"\n... ({remaining} more lines)" if remaining > 0 else ""
    )
    return _text(_truncate(f"{numbered}{suffix}"))


async def Write(file_path: str, content: str) -> ToolResponse:
    """Create or overwrite a text file, creating parent directories as needed.

    Args:
        file_path (str):
            Path to the file, absolute or relative to the project directory.
        content (str):
            The complete UTF-8 text to write.
    """
    workdir = Path.cwd().resolve()
    path = _resolve(workdir, file_path)
    try:
        _ensure_inside(workdir, path)
    except ValueError as exc:
        return _text(f"Error: {exc}")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return _text(f"Error: could not write {path}: {exc}")

    return _text(f"Wrote {len(content.encode('utf-8'))} bytes to {path}")


async def Edit(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> ToolResponse:
    """Replace an exact string in a file.

    Args:
        file_path (str):
            Path to the file, absolute or relative to the project directory.
        old_string (str):
            The exact text to replace.
        new_string (str):
            The replacement text.
        replace_all (bool):
            Replace every occurrence instead of requiring a unique match.
            Defaults to False.
    """
    workdir = Path.cwd().resolve()
    path = _resolve(workdir, file_path)
    try:
        _ensure_inside(workdir, path)
    except ValueError as exc:
        return _text(f"Error: {exc}")

    if not path.is_file():
        return _text(f"Error: file not found: {path}")
    if old_string == "":
        return _text("Error: old_string must not be empty.")
    if old_string == new_string:
        return _text("Error: old_string and new_string are identical.")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return _text(f"Error: could not read {path}: {exc}")

    occurrences = text.count(old_string)
    if occurrences == 0:
        return _text(f"Error: old_string was not found in {path}")
    if occurrences > 1 and not replace_all:
        return _text(
            f"Error: old_string occurs {occurrences} times in {path}. "
            "Provide more surrounding context or set replace_all=true."
        )

    updated = (
        text.replace(old_string, new_string)
        if replace_all
        else text.replace(old_string, new_string, 1)
    )
    try:
        path.write_text(updated, encoding="utf-8")
    except OSError as exc:
        return _text(f"Error: could not write {path}: {exc}")

    count = occurrences if replace_all else 1
    return _text(f"Replaced {count} occurrence(s) in {path}")


async def Glob(pattern: str, path: str = ".") -> ToolResponse:
    """Find files matching a glob pattern.

    Args:
        pattern (str):
            Glob pattern, e.g. `src/**/*.tsx` or `*.md`.
        path (str):
            Directory to search from. Defaults to the project directory.
    """
    workdir = Path.cwd().resolve()
    base = _resolve(workdir, path)
    if not base.is_dir():
        return _text(f"Error: directory not found: {base}")

    try:
        matches = [
            Path(match)
            for match in glob_module.glob(
                str(base / pattern), recursive=True
            )
        ]
    except (OSError, re.error) as exc:
        return _text(f"Error: invalid glob pattern: {exc}")

    files = [match for match in matches if match.is_file()]
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    files = files[:500]

    if not files:
        return _text(f"No files matched {pattern!r} under {base}")

    lines = []
    for item in files:
        try:
            displayed = item.resolve().relative_to(workdir)
        except ValueError:
            displayed = item
        lines.append(str(displayed))
    return _text("\n".join(lines))


def _iter_files(base: Path):
    if base.is_file():
        yield base
        return
    for root, dirs, files in os.walk(base):
        dirs[:] = [name for name in dirs if name not in SKIPPED_DIRS]
        for name in files:
            yield Path(root) / name


async def Grep(
    pattern: str,
    path: str = ".",
    glob: str = "",
    case_insensitive: bool = False,
    max_results: int = MAX_GREP_RESULTS,
) -> ToolResponse:
    """Search file contents with a regular expression.

    Args:
        pattern (str):
            Python regular expression to search for.
        path (str):
            File or directory to search. Defaults to the project directory.
        glob (str):
            Optional filename filter, e.g. `*.tsx`. Empty means all files.
        case_insensitive (bool):
            Perform a case-insensitive search. Defaults to False.
        max_results (int):
            Maximum number of matching lines to return. Defaults to 200.
    """
    workdir = Path.cwd().resolve()
    base = _resolve(workdir, path)
    if not base.exists():
        return _text(f"Error: path not found: {base}")

    try:
        regex = re.compile(
            pattern, re.IGNORECASE if case_insensitive else 0
        )
    except re.error as exc:
        return _text(f"Error: invalid regular expression: {exc}")

    max_results = max(1, min(int(max_results), 1000))
    results: list[str] = []

    for file_path in _iter_files(base):
        if glob and not fnmatch.fnmatch(file_path.name, glob):
            continue
        try:
            if file_path.stat().st_size > 5_000_000:
                continue
            data = file_path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:8192]:
            continue

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = _decode(data)

        try:
            displayed = file_path.resolve().relative_to(workdir)
        except ValueError:
            displayed = file_path

        for line_number, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                results.append(
                    f"{displayed}:{line_number}:{line.strip()[:500]}"
                )
                if len(results) >= max_results:
                    return _text(_truncate("\n".join(results)))

    if not results:
        return _text(f"No matches for {pattern!r} under {base}")
    return _text(_truncate("\n".join(results)))


def _html_to_text(raw: str) -> str:
    raw = re.sub(
        r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw
    )
    raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|section|article)>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
    text = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", text)


async def WebFetch(url: str, max_chars: int = 20_000) -> ToolResponse:
    """Fetch a URL and return readable text (HTML is converted to plain text).

    Args:
        url (str):
            The http(s) URL to fetch.
        max_chars (int):
            Maximum number of characters to return. Defaults to 20000.
    """
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return _text("Error: only http(s) URLs are supported.")

    try:
        import httpx
    except ImportError:  # pragma: no cover - agentscope depends on httpx
        return _text("Error: httpx is not installed.")

    max_chars = max(1000, min(int(max_chars), 100_000))
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "p2v-agent/0.1 (+https://remotion.dev)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" in content_type.lower():
                text = _html_to_text(response.text)
            else:
                text = response.text
    except Exception as exc:
        return _text(f"Error fetching {url}: {exc}")

    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [truncated]"
    return _text(text or "(empty response)")


def build_toolkit(workdir: Path) -> Toolkit:
    """Create a Toolkit with all coding tools registered.

    The agent's process working directory is changed to ``workdir`` before the
    tools are used (see :func:`p2v_agent.agent_runner.run_agent`), so relative
    paths resolve against the generated Remotion project.
    """

    toolkit = Toolkit()
    for tool in (Bash, Read, Write, Edit, Glob, Grep, WebFetch):
        toolkit.register_tool_function(tool)
    return toolkit
