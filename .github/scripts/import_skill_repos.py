#!/usr/bin/env python3
"""Import skills from external repositories into SkillsLobby and route them."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from route_skills import render_report as render_route_report
from route_skills import route_skills


ROOT = Path(__file__).resolve().parents[2]
SKILLS_LOBBY = ROOT / "SkillsLobby"

IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
}


@dataclass(frozen=True)
class SkillCandidate:
    repo_root: Path
    skill_dir: Path
    skill_file_name: str


@dataclass(frozen=True)
class ImportResult:
    source: str
    source_skill_dir: Path
    destination_skill_dir: Path
    normalized_skill_file: bool
    normalized_from: str | None


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        return str(resolved)


def unique_destination(base: Path) -> Path:
    if not base.exists():
        return base

    counter = 2
    while True:
        candidate = base.parent / f"{base.name}-{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def pick_skill_file_name(file_names: list[str]) -> str | None:
    lower_to_original = {name.lower(): name for name in file_names}
    for expected in ("skill.md", "skills.md"):
        if expected in lower_to_original:
            return lower_to_original[expected]
    return None


def discover_skill_candidates(repo_root: Path) -> list[SkillCandidate]:
    candidates: list[SkillCandidate] = []

    for current, dir_names, file_names in os.walk(repo_root):
        dir_names[:] = sorted(name for name in dir_names if name not in IGNORED_DIR_NAMES)
        skill_file_name = pick_skill_file_name(file_names)
        if skill_file_name is None:
            continue
        candidates.append(
            SkillCandidate(
                repo_root=repo_root,
                skill_dir=Path(current),
                skill_file_name=skill_file_name,
            )
        )

    return sorted(candidates, key=lambda item: str(item.skill_dir))


def source_name(source: str) -> str:
    normalized = source.rstrip("/\\")
    name = Path(normalized).name or "repository"
    if name.lower().endswith(".git"):
        name = name[:-4]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return name or "repository"


def clone_repository(source: str, checkout_parent: Path, clone_depth: int) -> Path:
    checkout_parent.mkdir(parents=True, exist_ok=True)
    destination = unique_destination(checkout_parent / source_name(source))
    command = [
        "git",
        "clone",
        "--depth",
        str(clone_depth),
        source,
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"Failed to clone source `{source}`: {stderr}")
    return destination.resolve()


def resolve_source_repository(source: str, checkout_parent: Path, clone_depth: int) -> Path:
    maybe_local = Path(source)
    if maybe_local.exists():
        if not maybe_local.is_dir():
            raise RuntimeError(f"Source exists but is not a directory: `{source}`")
        return maybe_local.resolve()
    return clone_repository(source, checkout_parent=checkout_parent, clone_depth=clone_depth)


def normalize_skill_file(skill_dir: Path, original_name: str) -> tuple[bool, str | None]:
    if original_name == "SKILL.md":
        return False, None

    source_file = skill_dir / original_name
    canonical = skill_dir / "SKILL.md"
    if not source_file.exists():
        return False, None
    if canonical.exists():
        return False, None

    source_file.rename(canonical)
    return True, original_name


def import_skill_candidate(candidate: SkillCandidate, destination_root: Path, source: str) -> ImportResult:
    destination = unique_destination(destination_root / candidate.skill_dir.name)
    shutil.copytree(candidate.skill_dir, destination)
    normalized, normalized_from = normalize_skill_file(destination, candidate.skill_file_name)
    return ImportResult(
        source=source,
        source_skill_dir=candidate.skill_dir,
        destination_skill_dir=destination,
        normalized_skill_file=normalized,
        normalized_from=normalized_from,
    )


def import_from_sources(sources: list[str], clone_depth: int, destination_root: Path) -> tuple[list[ImportResult], list[str]]:
    destination_root.mkdir(parents=True, exist_ok=True)

    imported: list[ImportResult] = []
    warnings: list[str] = []

    with tempfile.TemporaryDirectory(prefix="skill-import-sources-") as temp_root_raw:
        temp_root = Path(temp_root_raw)
        for source in sources:
            repo_root = resolve_source_repository(source, checkout_parent=temp_root, clone_depth=clone_depth)
            candidates = discover_skill_candidates(repo_root)
            if not candidates:
                warnings.append(f"No SKILL.md or SKILLS.md files found in source `{source}`.")
                continue

            for candidate in candidates:
                imported.append(
                    import_skill_candidate(
                        candidate=candidate,
                        destination_root=destination_root,
                        source=source,
                    )
                )

    return imported, warnings


def render_import_report(imported: list[ImportResult], warnings: list[str], source_count: int) -> str:
    lines = [
        "# Skill Import Report",
        "",
        f"Sources processed: `{source_count}`",
        f"Skills imported: `{len(imported)}`",
        "",
    ]

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    if not imported:
        lines.append("No skills were imported.")
        return "\n".join(lines)

    lines.extend(
        [
            "| Source | Imported Skill Folder | Destination | Normalized |",
            "|---|---|---|---|",
        ]
    )
    for item in imported:
        normalized_text = item.normalized_from if item.normalized_from else "no"
        lines.append(
            f"| `{item.source}` | `{display_path(item.source_skill_dir)}` | "
            f"`{display_path(item.destination_skill_dir)}` | `{normalized_text}` |"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import skill folders from local paths or git repos into SkillsLobby, "
            "then optionally run routing."
        )
    )
    parser.add_argument(
        "sources",
        nargs="+",
        help="One or more local repository paths or git clone URLs.",
    )
    parser.add_argument(
        "--clone-depth",
        type=int,
        default=1,
        help="Depth used when cloning remote sources (default: 1).",
    )
    parser.add_argument(
        "--skip-route",
        action="store_true",
        help="Import into SkillsLobby but skip route_skills execution.",
    )
    parser.add_argument(
        "--route-dry-run",
        action="store_true",
        help="Run route_skills in dry-run mode instead of applying moves.",
    )
    parser.add_argument(
        "--report-file",
        type=str,
        help="Optional path to write a combined markdown import and routing report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.clone_depth < 1:
        raise SystemExit("--clone-depth must be >= 1.")

    imported, warnings = import_from_sources(
        sources=args.sources,
        clone_depth=args.clone_depth,
        destination_root=SKILLS_LOBBY,
    )
    import_report = render_import_report(imported, warnings, source_count=len(args.sources))
    print(import_report)

    route_report = ""
    if args.skip_route:
        print("Routing skipped (`--skip-route`).")
    elif not imported:
        print("Routing skipped because no skills were imported.")
    else:
        _, routing_results = route_skills(dry_run=args.route_dry_run)
        route_report = render_route_report(routing_results, dry_run=args.route_dry_run)
        print(route_report)

    if args.report_file:
        report_path = Path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        combined = import_report
        if route_report:
            combined = f"{combined}\n\n{route_report}"
        report_path.write_text(combined, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
