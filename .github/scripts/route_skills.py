#!/usr/bin/env python3
"""Gate and route uploaded skills from SkillsLobby/ into taxonomy folders."""

from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS_LOBBY = ROOT / "SkillsLobby"
LIMBO_REVIEW = Path("Limbo") / "NeedsHumanReview"
FALLBACK = Path("Reference") / "Unsorted"
WORTHY_THRESHOLD = 70
TRIGGER_HINTS = ("use when", "when codex", "use for", "for tasks", "trigger")

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
class QualityResult:
    worthy: bool
    score: int
    summary: str


@dataclass
class RouteResult:
    skill: str
    source: str
    destination: str
    action: str
    gate: str
    score: int
    gate_reason: str
    routing_reason: str


def unique_destination(base: Path) -> Path:
    if not base.exists():
        return base
    counter = 2
    while True:
        candidate = base.parent / f"{base.name}-{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def split_frontmatter(content: str) -> tuple[dict[str, str], str, list[str]]:
    """Extract frontmatter keys and markdown body."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content, ["Frontmatter must start the file with `---`."]

    closing_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        return {}, content, ["Frontmatter opening `---` is missing a closing `---`."]

    frontmatter: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip().strip('"').strip("'")
        frontmatter[key] = value

    body = "\n".join(lines[closing_index + 1 :])
    return frontmatter, body, []


def assess_skill_worthiness(skill_dir: Path) -> QualityResult:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return QualityResult(
            worthy=False,
            score=0,
            summary="Missing `SKILL.md`; requires human review.",
        )

    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    findings: list[str] = []
    score = 0
    hard_fail = False

    frontmatter, body, frontmatter_issues = split_frontmatter(content)
    if frontmatter_issues:
        hard_fail = True
        findings.extend(frontmatter_issues)
    else:
        score += 20

    name = frontmatter.get("name", "").strip()
    description = frontmatter.get("description", "").strip()
    if name and description:
        score += 20
    else:
        hard_fail = True
        findings.append("Frontmatter must include non-empty `name` and `description`.")

    if description:
        lower_desc = description.lower()
        if any(hint in lower_desc for hint in TRIGGER_HINTS):
            score += 10
        else:
            findings.append("Description should include explicit trigger context (for example: `Use when ...`).")

    if len(body.strip()) >= 80:
        score += 15
    else:
        findings.append("Body content is too thin; add clear workflow guidance.")

    if re.search(r"(?m)^#\s+\S+", body):
        score += 10
    else:
        findings.append("Body should include a top-level `#` heading.")

    if re.search(r"(?m)^##\s+\S+", body):
        score += 10
    else:
        findings.append("Body should include at least one `##` section.")

    line_count = len(content.splitlines())
    if line_count <= 500:
        score += 10
    elif line_count <= 700:
        score += 5
        findings.append("SKILL.md is long (>500 lines); move details into references for progressive disclosure.")
    else:
        findings.append("SKILL.md exceeds 700 lines; split into focused references.")

    resource_dirs = [name for name in ("scripts", "references", "assets") if (skill_dir / name).is_dir()]
    if not resource_dirs:
        score += 15
    else:
        content_lower = content.lower()
        covered = 0
        missing = []
        for dirname in resource_dirs:
            if (
                f"{dirname}/" in content_lower
                or f"`{dirname}`" in content_lower
                or f"`{dirname}/`" in content_lower
            ):
                covered += 1
            else:
                missing.append(dirname)
        score += int(round((covered / len(resource_dirs)) * 15))
        if missing:
            findings.append(
                f"Resource folders exist but are not documented in SKILL.md: {', '.join(sorted(missing))}."
            )

    score = min(score, 100)
    worthy = score >= WORTHY_THRESHOLD and not hard_fail

    if worthy:
        summary = f"Worthy ({score}/100). Passed gate."
    else:
        summary = f"Not worthy ({score}/100). Sent to limbo for human review."
    if findings:
        summary = f"{summary} Key issues: {'; '.join(findings[:3])}"
    return QualityResult(worthy=worthy, score=score, summary=summary)


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


def render_report(results: list[RouteResult], dry_run: bool) -> str:
    def escape_cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", "<br>")

    header = "# Skill Routing Report"
    mode = f"Mode: {'dry-run' if dry_run else 'apply'}"
    if not results:
        return f"{header}\n\n{mode}\n\nNo skill folders were processed."

    lines = [
        header,
        "",
        mode,
        "",
        f"Worthy threshold: `{WORTHY_THRESHOLD}/100`",
        "",
        "| Skill | Gate | Score | Action | Destination | Gate Reason | Routing Reason |",
        "|---|---|---:|---|---|---|---|",
    ]
    for item in results:
        lines.append(
            f"| `{escape_cell(item.skill)}` | {escape_cell(item.gate)} | {item.score} | {escape_cell(item.action)} | `{escape_cell(item.destination)}` | {escape_cell(item.gate_reason)} | {escape_cell(item.routing_reason)} |"
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

        quality = assess_skill_worthiness(skill_dir)
        source = str(skill_dir.relative_to(ROOT))

        if quality.worthy:
            skill_md = skill_dir / "SKILL.md"
            destination_parent, routing_reason = classify_category(skill_dir, skill_md)
            action_base = "move"
        else:
            destination_parent = LIMBO_REVIEW
            routing_reason = "Held in limbo pending human assessment."
            action_base = "move-to-limbo"

        target_parent = ROOT / destination_parent
        target_parent.mkdir(parents=True, exist_ok=True)
        destination = unique_destination(target_parent / skill_dir.name)
        destination_relative = str(destination.relative_to(ROOT))

        if dry_run:
            print(f"[DRY-RUN] {source} -> {destination_relative}")
            action = f"would-{action_base}"
        else:
            shutil.move(str(skill_dir), str(destination))
            moved += 1
            print(f"Moved {source} -> {destination_relative}")
            action = action_base.replace("move", "moved", 1)

        results.append(
            RouteResult(
                skill=skill_dir.name,
                source=source,
                destination=destination_relative,
                action=action,
                gate="worthy" if quality.worthy else "limbo",
                score=quality.score,
                gate_reason=quality.summary,
                routing_reason=routing_reason,
            )
        )

    if dry_run:
        print("Dry-run routing complete.")
    elif moved == 0:
        print("No skill folders were moved.")
    return moved, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gate and route skills from SkillsLobby into taxonomy folders."
    )
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
