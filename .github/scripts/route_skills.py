#!/usr/bin/env python3
"""Route uploaded skills from Incoming/ into the best matching category."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INCOMING = ROOT / "Incoming"
FALLBACK = Path("Reference") / "Unsorted"

CATEGORY_ALIASES = {
    "bestpractices": Path("BestPractices"),
    "best_practices": Path("BestPractices"),
    "language": Path("LanguageSpecific"),
    "languagespecific": Path("LanguageSpecific"),
    "language_specific": Path("LanguageSpecific"),
    "linux": Path("PlatformSpecific") / "Linux",
    "windows": Path("PlatformSpecific") / "Windows",
    "macos": Path("PlatformSpecific") / "macOS",
    "osx": Path("PlatformSpecific") / "macOS",
    "designux": Path("DesignUX"),
    "uiux": Path("DesignUX"),
    "ui/ux": Path("DesignUX"),
    "tooling": Path("Tooling"),
    "workflowautomation": Path("WorkflowAutomation"),
    "workflow_automation": Path("WorkflowAutomation"),
    "automation": Path("WorkflowAutomation"),
    "reference": Path("Reference"),
}

KEYWORD_RULES = [
    (("figma", "wireframe", "accessibility", "design system", "ui", "ux"), Path("DesignUX")),
    (("powershell", "winget", "registry", "windows", "wsl"), Path("PlatformSpecific") / "Windows"),
    (("bash", "systemd", "apt", "linux", "debian", "ubuntu"), Path("PlatformSpecific") / "Linux"),
    (("homebrew", "xcode", "launchd", "macos", "osx"), Path("PlatformSpecific") / "macOS"),
    (
        ("python", "javascript", "typescript", "java", "go", "rust", "c#", "ruby", "php", "node"),
        Path("LanguageSpecific"),
    ),
    (("guideline", "checklist", "best practice", "convention", "standards"), Path("BestPractices")),
    (("github actions", "ci/cd", "terraform", "kubernetes", "docker", "tooling", "cli"), Path("Tooling")),
    (("pipeline", "orchestration", "automation", "workflow", "agent"), Path("WorkflowAutomation")),
]


def parse_declared_category(content: str) -> Path | None:
    """Allow explicit routing via 'Category: <value>' in SKILL.md."""
    for line in content.splitlines()[:60]:
        match = re.match(r"^\s*category\s*:\s*(.+?)\s*$", line, flags=re.IGNORECASE)
        if not match:
            continue
        key = re.sub(r"[^a-z0-9/_]+", "", match.group(1).strip().lower())
        return CATEGORY_ALIASES.get(key)
    return None


def classify_category(skill_dir: Path, skill_md: Path) -> Path:
    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    declared = parse_declared_category(content)
    if declared is not None:
        return declared

    text = f"{skill_dir.name}\n{content}".lower()
    best_path = FALLBACK
    best_score = 0
    for keywords, target in KEYWORD_RULES:
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_score = score
            best_path = target
    return best_path


def unique_destination(base: Path) -> Path:
    if not base.exists():
        return base
    counter = 2
    while True:
        candidate = base.parent / f"{base.name}-{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def route_skills() -> int:
    if not INCOMING.exists():
        print("Incoming/ does not exist. Nothing to route.")
        return 0

    moved = 0
    for skill_dir in sorted(INCOMING.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            print(f"Skipping {skill_dir.relative_to(ROOT)} (no SKILL.md).")
            continue

        category = classify_category(skill_dir, skill_md)
        target_parent = ROOT / category
        target_parent.mkdir(parents=True, exist_ok=True)

        destination = unique_destination(target_parent / skill_dir.name)
        shutil.move(str(skill_dir), str(destination))
        moved += 1
        print(f"Moved {skill_dir.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")

    if moved == 0:
        print("No skill folders were moved.")
    return moved


if __name__ == "__main__":
    route_skills()
