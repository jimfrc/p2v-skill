"""Pick a local Chromium browser for Remotion.

Remotion normally downloads a 130+ MB Chrome Headless Shell on first render.
On slow or restricted networks that download can take a very long time (or
fail).  If a local Chrome/Chromium/Edge is available, point Remotion at it via
``Config.setBrowserExecutable()`` so rendering can start immediately.

Set ``P2V_BROWSER_EXECUTABLE`` to override the detected path, or to ``off`` /
``none`` to force Remotion's own download.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

_DISABLE_VALUES = {"", "0", "false", "no", "off", "none", "auto"}

_WINDOWS_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

_MACOS_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

_LINUX_COMMANDS = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "microsoft-edge-stable",
]


def _env_override() -> Optional[str]:
    for name in ("P2V_BROWSER_EXECUTABLE", "REMOTION_BROWSER_EXECUTABLE"):
        value = os.environ.get(name)
        if value is not None:
            return value.strip()
    return None


def find_browser_executable() -> Optional[Path]:
    """Return a usable local Chromium executable, or ``None``.

    ``P2V_BROWSER_EXECUTABLE`` / ``REMOTION_BROWSER_EXECUTABLE`` wins over
    auto-detection.  Values ``off``, ``none``, ``0`` and ``false`` disable the
    override and therefore disable auto-detection too.
    """

    override = _env_override()
    if override is not None:
        if override.lower() in _DISABLE_VALUES:
            return None
        path = Path(override).expanduser()
        if path.is_file():
            return path.resolve()
        print(
            f"[build] WARNING: P2V_BROWSER_EXECUTABLE points to a missing "
            f"file: {path}"
        )
        return None

    candidates: list[Path] = []

    if sys.platform == "win32":
        candidates.extend(Path(item) for item in _WINDOWS_CANDIDATES)
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(
                Path(local_app_data)
                / "Google"
                / "Chrome"
                / "Application"
                / "chrome.exe"
            )
    elif sys.platform == "darwin":
        candidates.extend(Path(item) for item in _MACOS_CANDIDATES)
    else:
        for command in _LINUX_COMMANDS:
            found = shutil.which(command)
            if found:
                candidates.append(Path(found))

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def configure_remotion_browser(project_dir: Path) -> Optional[Path]:
    """Add ``Config.setBrowserExecutable(...)`` to ``remotion.config.ts``.

    Returns the browser path when one was configured.  Existing user-defined
    ``setBrowserExecutable`` calls are respected and left untouched.
    """

    project_dir = Path(project_dir)
    browser = find_browser_executable()
    if browser is None:
        print(
            "[build] No local Chrome/Chromium/Edge found. Remotion will "
            "download Chrome Headless Shell (this can be slow). Set "
            "P2V_BROWSER_EXECUTABLE to a browser path to avoid the download."
        )
        return None

    config_path = project_dir / "remotion.config.ts"
    if not config_path.is_file():
        config_path.write_text(
            'import { Config } from "@remotion/cli/config";\n',
            encoding="utf-8",
        )

    content = config_path.read_text(encoding="utf-8")
    if "setBrowserExecutable" in content:
        print(f"[build] Remotion browser already configured in {config_path}")
        return browser

    if 'from "@remotion/cli/config"' not in content:
        content = (
            'import { Config } from "@remotion/cli/config";\n' + content
        )

    browser_literal = json.dumps(str(browser))
    content = content.rstrip() + (
        "\n\n// p2v-agent: use the locally installed browser instead of\n"
        "// downloading Chrome Headless Shell (slow on restricted networks).\n"
        f"Config.setBrowserExecutable({browser_literal});\n"
    )
    config_path.write_text(content, encoding="utf-8")
    print(f"[build] Remotion browser: {browser}")
    return browser
