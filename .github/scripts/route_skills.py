#!/usr/bin/env python3
"""Route uploaded skills from SkillsLobby/ into the best matching category."""

from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS_LOBBY = ROOT / "SkillsLobby"
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


@dataclass
class RouteResult:
    skill: str
    source: str
    destination: str
    action: str
    reason: str


def parse_declared_category(content: str) -> tuple[Path | None, str | None]:
    """Allow explicit routing via 'Category: <value>' in SKILL.md."""
    for line in content.splitlines()[:60]:
        match = re.match(r"^\s*category\s*:\s*(.+?)\s*$", line, flags=re.IGNORECASE)
        if not match:
            continue
        raw_value = match.group(1).strip()
        key = re.sub(r"[^a-z0-9/_]+", "", raw_value.lower())
        return CATEGORY_ALIASES.get(key), raw_value
    return None, None


def classify_category(skill_dir: Path, skill_md: Path) -> tuple[Path, str]:
    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    declared, raw_declared = parse_declared_category(content)
    if declared is not None:
        return declared, f"Declared category matched: `{raw_declared}`"
    if raw_declared is not None:
        return FALLBACK, f"Declared category not recognized: `{raw_declared}`"

    text = f"{skill_dir.name}\n{content}".lower()
    best_path = FALLBACK
    best_score = 0
    best_keywords: tuple[str, ...] = ()
    for keywords, target in KEYWORD_RULES:
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_score = score
            best_path = target
            best_keywords = tuple(keyword for keyword in keywords if keyword in text)

    if best_score > 0:
        return best_path, f"Keyword match score {best_score}: {', '.join(best_keywords)}"
    return FALLBACK, "No category declaration and no keyword hit; sent to fallback."


def unique_destination(base: Path) -> Path:
    if not base.exists():
        return base
    counter = 2
    while True:
        candidate = base.parent / f"{base.name}-{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def render_report(results: list[RouteResult], dry_run: bool) -> str:
    header = "# Skill Routing Report"
    mode = f"Mode: {'dry-run' if dry_run else 'apply'}"
    if not results:
        return f"{header}\n\n{mode}\n\nNo skill folders were processed."

    lines = [header, "", mode, "", "| Skill | Action | Destination | Reason |", "|---|---|---|---|"]
    for item in results:
        lines.append(
            f"| `{item.skill}` | {item.action} | `{item.destination}` | {item.reason} |"
        )
    return "\n".join(lines)


def route_skills(dry_run: bool = False) -> tuple[int, list[RouteResult]]:
    if not SKILLS_LOBBY.exists():
        print("SkillsLobby/ does not exist. Nothing to route.")
        return 0, []

    moved = 0
    results: list[RouteResult] = []
    for skill_dir in sorted(SKILLS_LOBBY.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            relative_skill = str(skill_dir.relative_to(ROOT))
            print(f"Skipping {relative_skill} (no SKILL.md).")
            results.append(
                RouteResult(
                    skill=skill_dir.name,
                    source=relative_skill,
                    destination=relative_skill,
                    action="skipped",
                    reason="Missing `SKILL.md`.",
                )
            )
            continue

        category, reason = classify_category(skill_dir, skill_md)
        target_parent = ROOT / category
        target_parent.mkdir(parents=True, exist_ok=True)

        destination = unique_destination(target_parent / skill_dir.name)
        relative_source = str(skill_dir.relative_to(ROOT))
        relative_destination = str(destination.relative_to(ROOT))

        if dry_run:
            print(f"[DRY-RUN] {relative_source} -> {relative_destination}")
            results.append(
                RouteResult(
                    skill=skill_dir.name,
                    source=relative_source,
                    destination=relative_destination,
                    action="would-move",
                    reason=reason,
                )
            )
            continue

        shutil.move(str(skill_dir), str(destination))
        moved += 1
        print(f"Moved {relative_source} -> {relative_destination}")
        results.append(
            RouteResult(
                skill=skill_dir.name,
                source=relative_source,
                destination=relative_destination,
                action="moved",
                reason=reason,
            )
        )

    if dry_run:
        print("Dry-run routing complete.")
    elif moved == 0:
        print("No skill folders were moved.")
    return moved, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Route skills from SkillsLobby into taxonomy folders.")
    parser.add_argument("--dry-run", action="store_true", help="Do not move folders; only produce a report.")
    parser.add_argument("--report-file", type=str, help="Optional path for markdown routing report.")
    args = parser.parse_args()

    _, report_items = route_skills(dry_run=args.dry_run)
    report = render_report(report_items, dry_run=args.dry_run)
    print(report)

    if args.report_file:
        report_path = Path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
