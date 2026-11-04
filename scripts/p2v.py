#!/usr/bin/env python3
"""Bootstrap and run the vendored p2v-agent CLI.

The first run copies the vendored project into a per-user cache directory,
creates a virtualenv there, and installs the package and its dependencies.
Later runs reuse the cache. The skill folder itself is never written to, so it
can live in a read-only location. If the vendored source changes, the cached
copy and the editable install are refreshed automatically.

Examples:
    python scripts/p2v.py --check
    python scripts/p2v.py build --prompt-file prompt.txt -o outputs
    python scripts/p2v.py install ~/.claude
    python scripts/p2v.py --bootstrap-only
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
VENDOR_DIR = SKILL_ROOT / "vendor" / "p2v-agent"
VENDOR_SKILLS_DIR = VENDOR_DIR / "skills"
MARKER_NAME = "p2v-agent-skill.json"

MIN_PYTHON = (3, 10)
MIN_NODE = (20, 12)

# Kept in sync with pyproject.toml's dependencies. Used only for the error hint.
DEPENDENCY_HINT = "agentscope, mcp, tqdm, python-dotenv"

API_KEY_VARS = (
    "P2V_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "DASHSCOPE_API_KEY",
)

IGNORED_VENDOR_NAMES = {
    ".env",
    ".venv",
    "__pycache__",
    "outputs",
}
IGNORED_VENDOR_SUFFIXES = {".pyc", ".pyo"}
IGNORED_VENDOR_DIR_SUFFIXES = (".egg-info",)


def _print(message: str = "") -> None:
    print(message, flush=True)


def _run(command: list[str], **kwargs: object) -> None:
    _print("[p2v-skill] $ " + " ".join(str(part) for part in command))
    subprocess.run(command, check=True, **kwargs)


def _cache_dir() -> Path:
    override = os.environ.get("P2V_SKILL_HOME", "").strip()
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "p2v-agent-skill"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "p2v-agent-skill"

    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "p2v-agent-skill"


def _venv_dir() -> Path:
    override = os.environ.get("P2V_SKILL_VENV", "").strip()
    if override:
        return Path(override).expanduser()
    return _cache_dir() / "venv"


def _runtime_vendor_dir() -> Path:
    override = os.environ.get("P2V_SKILL_VENDOR", "").strip()
    if override:
        return Path(override).expanduser()
    return _cache_dir() / "vendor" / "p2v-agent"


def _venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _marker_path(venv: Path) -> Path:
    return venv / MARKER_NAME


def _marker_data(venv: Path) -> dict:
    try:
        return json.loads(_marker_path(venv).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_marker(venv: Path, vendor_hash: str) -> None:
    _marker_path(venv).write_text(
        json.dumps(
            {
                "vendor": str(VENDOR_DIR.resolve()),
                "vendor_hash": vendor_hash,
                "skill_root": str(SKILL_ROOT),
                "runtime_vendor": str(_runtime_vendor_dir().resolve()),
                "python": "%d.%d.%d" % sys.version_info[:3],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _vendor_hash() -> str:
    """Content hash of the vendored project, ignoring caches and secrets."""

    digest = hashlib.sha256()
    for path in sorted(VENDOR_DIR.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(VENDOR_DIR)
        if any(
            part in IGNORED_VENDOR_NAMES
            or part.endswith(IGNORED_VENDOR_DIR_SUFFIXES)
            for part in relative.parts
        ):
            continue
        if path.suffix in IGNORED_VENDOR_SUFFIXES:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _require_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        required = "%d.%d" % MIN_PYTHON
        current = "%d.%d.%d" % sys.version_info[:3]
        raise SystemExit(
            f"p2v-agent-skill requires Python >= {required}; found {current}."
        )


def _require_vendor() -> None:
    missing = [
        path
        for path in (
            VENDOR_DIR / "pyproject.toml",
            VENDOR_DIR / "src" / "p2v_agent" / "__init__.py",
            VENDOR_SKILLS_DIR,
        )
        if not path.exists()
    ]
    if missing:
        raise SystemExit(
            "The vendored p2v-agent project is incomplete. Missing:\n"
            + "\n".join(f"  - {path}" for path in missing)
        )


def _sync_runtime_vendor(vendor_hash: str) -> Path:
    """Copy the vendored source into the cache and return the copy's path."""

    runtime = _runtime_vendor_dir()
    if runtime.exists():
        _print(f"[p2v-skill] Refreshing cached source copy: {runtime}")
        shutil.rmtree(runtime)
    else:
        _print(f"[p2v-skill] Caching source copy: {runtime}")

    ignore = shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.egg-info",
        ".venv",
        ".env",
        "outputs",
    )
    shutil.copytree(VENDOR_DIR, runtime, ignore=ignore)
    _write_runtime_marker(runtime, vendor_hash)
    return runtime


def _write_runtime_marker(runtime: Path, vendor_hash: str) -> None:
    (runtime / ".p2v-skill-hash").write_text(vendor_hash + "\n", encoding="utf-8")


def _runtime_is_current(runtime: Path, vendor_hash: str) -> bool:
    marker = runtime / ".p2v-skill-hash"
    if not (runtime / "src" / "p2v_agent" / "__init__.py").is_file():
        return False
    try:
        return marker.read_text(encoding="utf-8").strip() == vendor_hash
    except OSError:
        return False


def _pip_install_package(python: Path, runtime: Path) -> None:
    try:
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "-e",
                str(runtime),
                "--disable-pip-version-check",
            ]
        )
    except subprocess.CalledProcessError:
        _print(
            "[p2v-skill] Editable install failed; retrying as a regular "
            "install. The cached source is still used via PYTHONPATH."
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                str(runtime),
                "--disable-pip-version-check",
            ]
        )


def ensure_venv(force: bool = False) -> Path:
    """Prepare the cached source and venv; return the venv's Python."""

    _require_python_version()
    _require_vendor()

    vendor_hash = _vendor_hash()
    venv = _venv_dir()
    python = _venv_python(venv)
    runtime = _runtime_vendor_dir()
    marker = _marker_data(venv)

    if not force and python.is_file() and marker:
        if marker.get("vendor_hash") == vendor_hash and _runtime_is_current(
            runtime, vendor_hash
        ):
            return python
        if marker.get("vendor_hash"):
            # We own this venv: refresh the source copy and reinstall just the
            # package (dependencies are already present).
            _print("[p2v-skill] Vendored source changed; refreshing the venv.")
            _sync_runtime_vendor(vendor_hash)
            _write_marker(venv, vendor_hash)
            _pip_install_package(python, runtime)
            _write_marker(venv, vendor_hash)
            return python

    if venv.exists() and not _marker_path(venv).is_file():
        raise SystemExit(
            f"Refusing to delete {venv}: it exists but was not created by "
            "p2v-agent-skill. Remove it yourself or point P2V_SKILL_VENV at a "
            "different path."
        )

    if venv.exists():
        _print(f"[p2v-skill] Removing old virtualenv: {venv}")
        shutil.rmtree(venv)

    _sync_runtime_vendor(vendor_hash)

    _print(f"[p2v-skill] Creating virtualenv: {venv}")
    _run([sys.executable, "-m", "venv", str(venv)])
    python = _venv_python(venv)
    # Mark ownership immediately so an interrupted install can be repaired.
    _write_marker(venv, vendor_hash)

    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "--disable-pip-version-check",
        ]
    )

    _print(
        "[p2v-skill] Installing p2v-agent and its dependencies "
        f"({DEPENDENCY_HINT}); the first run can take several minutes."
    )
    _pip_install_package(python, runtime)
    _write_marker(venv, vendor_hash)
    return python


def _parse_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _node_status() -> tuple[str | None, str | None, tuple[int, int, int] | None]:
    node = shutil.which("node")
    npx = shutil.which("npx")
    version = None
    if node:
        try:
            completed = subprocess.run(
                [node, "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            version = _parse_version(completed.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            version = None
    return node, npx, version


def _bundled_skills() -> list[Path]:
    if not VENDOR_SKILLS_DIR.is_dir():
        return []
    return sorted(
        path
        for path in VENDOR_SKILLS_DIR.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def _browser_path() -> Path | None:
    runtime_src = _runtime_vendor_dir() / "src"
    source = runtime_src if runtime_src.is_dir() else VENDOR_DIR / "src"
    sys.path.insert(0, str(source))
    try:
        from p2v_agent.browser import find_browser_executable

        return find_browser_executable()
    except Exception:
        return None
    finally:
        try:
            sys.path.remove(str(source))
        except ValueError:
            pass


def check() -> int:
    """Validate the machine and the package without calling a model."""

    ok = True
    _print("p2v-agent-skill environment check")
    _print("----------------------------------")

    python_version = "%d.%d.%d" % sys.version_info[:3]
    if sys.version_info < MIN_PYTHON:
        _print(f"[FAIL] Python {python_version} (need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
        ok = False
    else:
        _print(f"[ok]   Python {python_version}")

    node, npx, node_version = _node_status()
    if node is None:
        _print(f"[FAIL] node not found (need >= {MIN_NODE[0]}.{MIN_NODE[1]})")
        ok = False
    elif node_version is None:
        _print(f"[WARN] node found at {node}, but its version could not be parsed")
    elif node_version < MIN_NODE:
        found = ".".join(str(part) for part in node_version)
        _print(f"[FAIL] Node.js {found} (need >= {MIN_NODE[0]}.{MIN_NODE[1]})")
        ok = False
    else:
        found = ".".join(str(part) for part in node_version)
        _print(f"[ok]   Node.js {found} ({node})")

    if npx is None:
        _print("[FAIL] npx not found on PATH")
        ok = False
    else:
        _print(f"[ok]   npx ({npx})")

    if not VENDOR_DIR.is_dir():
        _print(f"[FAIL] vendored project missing: {VENDOR_DIR}")
        return 1

    skills = _bundled_skills()
    if skills:
        _print(f"[ok]   bundled skills: {len(skills)} ({VENDOR_SKILLS_DIR})")
    else:
        _print(f"[FAIL] no bundled skills with SKILL.md under {VENDOR_SKILLS_DIR}")
        ok = False

    venv = _venv_dir()
    runtime = _runtime_vendor_dir()
    marker = _marker_data(venv)
    vendor_hash = _vendor_hash()

    if not _marker_path(venv).is_file():
        if venv.exists():
            _print(f"[WARN] foreign directory at venv path (will not be touched): {venv}")
        else:
            _print(f"[info] virtualenv will be created on first run: {venv}")
    elif marker.get("vendor_hash") != vendor_hash:
        _print("[WARN] vendored source changed; the venv will be refreshed on the next run")
    elif not _runtime_is_current(runtime, vendor_hash):
        _print("[WARN] cached source copy is incomplete; it will be recreated on the next run")
    else:
        _print(f"[ok]   virtualenv ready: {venv}")

    if _runtime_is_current(runtime, vendor_hash):
        _print(f"[ok]   cached source: {runtime}")
    else:
        _print(f"[info] source will be cached at: {runtime}")

    present = [name for name in API_KEY_VARS if os.environ.get(name)]
    if present:
        _print("[ok]   API key variable(s) set: " + ", ".join(present))
    else:
        _print(
            "[WARN] no API key variable is set in this shell. Put .env in the "
            "working directory or export one of: " + ", ".join(API_KEY_VARS)
        )

    browser = _browser_path()
    if browser:
        _print(f"[ok]   local browser for Remotion: {browser}")
    else:
        _print(
            "[info] no local Chrome/Chromium/Edge found; Remotion may download "
            "Chrome Headless Shell on first render."
        )

    _print("----------------------------------")
    _print("Result: " + ("ready" if ok else "missing prerequisites"))
    return 0 if ok else 1


def _print_help() -> None:
    _print(
        """p2v-agent-skill launcher

Usage:
  scripts/run.sh <p2v-agent arguments...>        # macOS / Linux
  scripts\\run.ps1 <p2v-agent arguments...>       # Windows PowerShell

Wrapper options:
  --check             Validate Python/Node/npx, bundled skills, env, browser.
  --bootstrap-only    Create/repair the venv and print its Python path.
  -h, --help          Show this help (the p2v-agent CLI help is below).
  --cli-help          Show the p2v-agent CLI help.

Everything else is forwarded to the p2v-agent CLI, for example:
  build --prompt-file prompt.txt --output-dir outputs
  build --dry-run --prompt-file prompt.txt
  install ~/.claude

Outputs (default --output-dir ./outputs):
  p2v_agent_<timestamp>_video.mp4
  p2v_agent_<timestamp>_slides.pdf
  p2v_agent_<timestamp>_video.agent_events.jsonl
"""
    )


def _forward(python: Path, arguments: list[str]) -> int:
    runtime_src = _runtime_vendor_dir() / "src"
    source_dir = runtime_src if runtime_src.is_dir() else VENDOR_DIR / "src"

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(source_dir) + (os.pathsep + existing if existing else "")
    env.setdefault("P2V_SKILL_ROOT", str(SKILL_ROOT))
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")

    command = [str(python), "-m", "p2v_agent", *arguments]
    _print("[p2v-skill] $ " + " ".join(command))
    try:
        return subprocess.call(command, env=env)
    except KeyboardInterrupt:
        _print("\n[p2v-skill] interrupted.")
        return 130


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)

    if not arguments or arguments[0] in {"-h", "--help", "help"}:
        _print_help()
        return 0
    if arguments[0] == "--check":
        return check()
    if arguments[0] == "--bootstrap-only":
        python = ensure_venv()
        _print(f"[p2v-skill] venv python: {python}")
        _print(f"[p2v-skill] cached source: {_runtime_vendor_dir()}")
        return 0
    if arguments[0] == "--cli-help":
        return _forward(ensure_venv(), ["--help"])

    return _forward(ensure_venv(), arguments)


if __name__ == "__main__":
    raise SystemExit(main())
