from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from p2v_agent.build import read_prompt
from p2v_agent.prompts import wrap_user_prompt


class PromptTests(unittest.TestCase):
    def test_prompt_file_strips_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt.txt"
            path.write_bytes("﻿topic: quantum\n".encode("utf-8"))
            self.assertEqual(read_prompt(str(path)), "topic: quantum")

    def test_wrap_prompt_pins_outputs(self) -> None:
        wrapped = wrap_user_prompt("topic: quantum physics")
        self.assertIn("prompt2video skill", wrapped)
        self.assertIn("quantum physics", wrapped)
        self.assertIn("out/video.mp4", wrapped)
        self.assertIn("out/slides.pdf", wrapped)


if __name__ == "__main__":
    unittest.main()
