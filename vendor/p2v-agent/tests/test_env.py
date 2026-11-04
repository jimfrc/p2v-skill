from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from p2v_agent.env import load_env_files


class EnvTests(unittest.TestCase):
    def test_loads_dotenv_from_cwd_without_overriding_real_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / ".env").write_text(
                "DEEPSEEK_API_KEY=from-dotenv\n"
                "DEEPSEEK_MODEL=from-dotenv-model\n",
                encoding="utf-8",
            )
            old_cwd = Path.cwd()
            os.chdir(tmp_path)
            try:
                with patch.dict(
                    os.environ, {"DEEPSEEK_MODEL": "from-env"}, clear=True
                ):
                    with patch(
                        "p2v_agent.env.repo_root",
                        return_value=tmp_path / "no-repo",
                    ):
                        loaded = load_env_files()

                    self.assertTrue(
                        any(
                            Path(path).resolve() == (tmp_path / ".env").resolve()
                            for path in loaded
                        )
                    )
                    self.assertEqual(
                        os.environ["DEEPSEEK_API_KEY"], "from-dotenv"
                    )
                    # Real environment variables take precedence.
                    self.assertEqual(
                        os.environ["DEEPSEEK_MODEL"], "from-env"
                    )
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
