from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentscope.tool import Toolkit

from p2v_agent.paths import (
    bundled_remotion_skill_dirs,
    bundled_skills_dir,
    prompt2video_skill_dir,
)
from p2v_agent.skills import (
    discover_skill_dirs,
    install_bundled_skills,
    list_skills,
    read_skill_metadata,
    register_skills,
)

SKILL_MD = """---
name: {name}
description: {description}
---

# {name}
Do the thing.
"""


class SkillTests(unittest.TestCase):
    def test_bundled_skill_is_present(self) -> None:
        skills_dir = bundled_skills_dir()
        self.assertTrue((skills_dir / "prompt2video" / "SKILL.md").is_file())
        self.assertEqual(prompt2video_skill_dir().name, "prompt2video")

    def test_bundled_remotion_skills_are_present(self) -> None:
        skill_dirs = bundled_remotion_skill_dirs()
        self.assertTrue(skill_dirs)
        names = {path.name for path in skill_dirs}
        self.assertIn("remotion-best-practices", names)
        self.assertIn("remotion-render", names)
        for path in skill_dirs:
            self.assertTrue((path / "SKILL.md").is_file())

    def test_read_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "demo"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                SKILL_MD.format(name="demo", description="A demo skill"),
                encoding="utf-8",
            )
            skill = read_skill_metadata(skill_dir)
            self.assertEqual(skill.name, "demo")
            self.assertEqual(skill.description, "A demo skill")

    def test_discover_and_register(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            for index in range(2):
                skill_dir = root / f"skill{index}"
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    SKILL_MD.format(
                        name=f"skill{index}", description=f"Skill {index}"
                    ),
                    encoding="utf-8",
                )

            discovered = discover_skill_dirs([root])
            self.assertEqual(len(discovered), 2)
            self.assertEqual(
                [skill.name for skill in list_skills([root])],
                ["skill0", "skill1"],
            )

            toolkit = Toolkit()
            registered = register_skills(toolkit, [root])
            self.assertEqual(len(registered), 2)
            prompt = toolkit.get_agent_skill_prompt()
            self.assertIn("skill0", prompt)

    def test_install_bundled_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            installed = install_bundled_skills(bundled_skills_dir(), Path(tmp))
            self.assertTrue(installed)
            self.assertTrue((Path(tmp) / "skills" / "prompt2video" / "SKILL.md").is_file())
            self.assertTrue(
                (Path(tmp) / "skills" / "remotion-best-practices" / "SKILL.md").is_file()
            )


if __name__ == "__main__":
    unittest.main()
