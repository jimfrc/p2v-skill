from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from p2v_agent.tools import (
    Bash,
    Edit,
    Glob,
    Grep,
    Read,
    Write,
    _decode,
)


def _run(coro):
    return asyncio.run(coro)


def _text(response) -> str:
    return response.content[0]["text"]


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old_cwd = Path.cwd()
        os.chdir(self._tmp.name)
        self.workdir = Path(self._tmp.name)

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def test_write_read_roundtrip(self) -> None:
        result = _run(Write("src/hello.txt", "line one\nline two\n"))
        self.assertIn("Wrote", _text(result))
        self.assertTrue((self.workdir / "src" / "hello.txt").is_file())

        result = _run(Read("src/hello.txt"))
        text = _text(result)
        self.assertIn("1\tline one", text)
        self.assertIn("2\tline two", text)

    def test_edit_unique_and_replace_all(self) -> None:
        _run(Write("a.txt", "foo bar foo"))

        result = _run(Edit("a.txt", "foo", "baz"))
        self.assertIn("occurs 2 times", _text(result))

        result = _run(Edit("a.txt", "foo", "baz", replace_all=True))
        self.assertIn("Replaced 2", _text(result))
        self.assertEqual((self.workdir / "a.txt").read_text(), "baz bar baz")

    def test_write_outside_project_is_refused(self) -> None:
        outside = str(self.workdir.parent / "outside.txt")
        result = _run(Write(outside, "nope"))
        self.assertIn("Refusing to write outside", _text(result))
        self.assertFalse(Path(outside).exists())

    def test_glob_and_grep(self) -> None:
        _run(Write("src/one.ts", "export const alpha = 1;\n"))
        _run(Write("src/two.tsx", "export const beta = 2;\n"))
        _run(Write("src/readme.md", "alpha docs\n"))

        glob_text = _text(_run(Glob("src/**/*.ts*")))
        self.assertIn("one.ts", glob_text)
        self.assertIn("two.tsx", glob_text)
        self.assertNotIn("readme.md", glob_text)

        grep_text = _text(_run(Grep("alpha", path="src", glob="*.ts")))
        self.assertIn("one.ts:1:", grep_text)
        self.assertNotIn("readme.md", grep_text)

    def test_bash_echo(self) -> None:
        result = _run(Bash("echo hello-p2v"))
        text = _text(result)
        self.assertIn("<returncode>0</returncode>", text)
        self.assertIn("hello-p2v", text)

    def test_decode_gbk(self) -> None:
        self.assertIn("中文", _decode("中文".encode("gbk")))


if __name__ == "__main__":
    unittest.main()
