from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from p2v_agent.browser import (
    configure_remotion_browser,
    find_browser_executable,
)


class BrowserTests(unittest.TestCase):
    def test_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "browser.exe"
            fake.write_bytes(b"")
            with patch.dict(
                os.environ, {"P2V_BROWSER_EXECUTABLE": str(fake)}, clear=True
            ):
                found = find_browser_executable()
            self.assertEqual(found, fake.resolve())

    def test_env_off_disables_detection(self) -> None:
        with patch.dict(
            os.environ, {"P2V_BROWSER_EXECUTABLE": "off"}, clear=True
        ):
            self.assertIsNone(find_browser_executable())

    def test_configure_appends_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            config = project / "remotion.config.ts"
            config.write_text(
                "Config.setRspack(true);\n", encoding="utf-8"
            )
            fake = Path(r"C:\Program Files\Test\browser.exe")
            with patch(
                "p2v_agent.browser.find_browser_executable",
                return_value=fake,
            ):
                result = configure_remotion_browser(project)

            content = config.read_text(encoding="utf-8")
            self.assertEqual(result, fake)
            self.assertIn('from "@remotion/cli/config"', content)
            self.assertIn(
                'Config.setBrowserExecutable("C:\\\\Program Files\\\\Test'
                '\\\\browser.exe");',
                content,
            )
            self.assertIn("Config.setRspack(true);", content)

    def test_existing_browser_config_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            config = project / "remotion.config.ts"
            original = (
                'import { Config } from "@remotion/cli/config";\n'
                'Config.setBrowserExecutable("/custom/chrome");\n'
            )
            config.write_text(original, encoding="utf-8")
            with patch(
                "p2v_agent.browser.find_browser_executable",
                return_value=Path("/detected/chrome"),
            ):
                configure_remotion_browser(project)
            self.assertEqual(
                config.read_text(encoding="utf-8"), original
            )


if __name__ == "__main__":
    unittest.main()
