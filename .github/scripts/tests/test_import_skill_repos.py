import shutil
import tempfile
import unittest
from pathlib import Path

import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from import_skill_repos import SkillCandidate, discover_skill_candidates, import_skill_candidate  # noqa: E402


class ImportSkillReposTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="import-skill-repos-tests-"))
        self.repo_root = self.temp_dir / "source-repo"
        self.repo_root.mkdir(parents=True, exist_ok=True)
        self.lobby = self.temp_dir / "SkillsLobby"
        self.lobby.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_skill(self, parent: Path, filename: str, name: str = "SampleSkill") -> Path:
        parent.mkdir(parents=True, exist_ok=True)
        content = (
            "---\n"
            f"name: {name}\n"
            "description: Use when Codex needs workflow guidance.\n"
            "---\n\n"
            f"# {name}\n\n"
            "## Steps\n\n"
            "Run this workflow.\n"
        )
        target = parent / filename
        target.write_text(content, encoding="utf-8")
        return target

    def test_discover_skill_candidates_finds_skill_and_skills(self) -> None:
        self._write_skill(self.repo_root / "SkillA", "SKILLS.md", name="SkillA")
        self._write_skill(self.repo_root / "SkillB", "SKILL.md", name="SkillB")
        self._write_skill(self.repo_root / ".git" / "HiddenSkill", "SKILLS.md", name="HiddenSkill")

        candidates = discover_skill_candidates(self.repo_root)
        discovered = {(item.skill_dir.name, item.skill_file_name) for item in candidates}

        self.assertEqual(
            discovered,
            {
                ("SkillA", "SKILLS.md"),
                ("SkillB", "SKILL.md"),
            },
        )

    def test_import_skill_candidate_normalizes_skills_md(self) -> None:
        skill_dir = self.repo_root / "ImportMe"
        self._write_skill(skill_dir, "SKILLS.md", name="ImportMe")
        (skill_dir / "references").mkdir(parents=True, exist_ok=True)
        (skill_dir / "references" / "note.md").write_text("hello", encoding="utf-8")

        result = import_skill_candidate(
            candidate=SkillCandidate(
                repo_root=self.repo_root,
                skill_dir=skill_dir,
                skill_file_name="SKILLS.md",
            ),
            destination_root=self.lobby,
            source=str(self.repo_root),
        )

        self.assertTrue(result.normalized_skill_file)
        self.assertEqual(result.normalized_from, "SKILLS.md")
        self.assertTrue((result.destination_skill_dir / "SKILL.md").exists())
        self.assertFalse((result.destination_skill_dir / "SKILLS.md").exists())
        self.assertTrue((result.destination_skill_dir / "references" / "note.md").exists())

    def test_import_skill_candidate_uses_unique_destination(self) -> None:
        existing = self.lobby / "DuplicateSkill"
        self._write_skill(existing, "SKILL.md", name="ExistingSkill")

        source_skill_dir = self.repo_root / "DuplicateSkill"
        self._write_skill(source_skill_dir, "SKILL.md", name="DuplicateSkill")

        candidate = SkillCandidate(
            repo_root=self.repo_root,
            skill_dir=source_skill_dir,
            skill_file_name="SKILL.md",
        )

        first = import_skill_candidate(candidate=candidate, destination_root=self.lobby, source="repo-a")
        second = import_skill_candidate(candidate=candidate, destination_root=self.lobby, source="repo-a")

        self.assertEqual(first.destination_skill_dir.name, "DuplicateSkill-2")
        self.assertEqual(second.destination_skill_dir.name, "DuplicateSkill-3")
        self.assertTrue((first.destination_skill_dir / "SKILL.md").exists())
        self.assertTrue((second.destination_skill_dir / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
