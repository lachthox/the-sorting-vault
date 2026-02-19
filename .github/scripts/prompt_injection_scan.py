#!/usr/bin/env python3
"""Python-only prompt injection scanner for skill repositories."""

from __future__ import annotations

import argparse
import base64
import json
import math
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
SKILLS_LOBBY = ROOT / "SkillsLobby"
LIMBO_REVIEW = ROOT / "Limbo" / "NeedsHumanReview"
ALLOWLIST_FILE = ROOT / ".github" / "security" / "scan_allowlist.yml"

SWEEP_ROOTS = [
    ROOT / "BestPractices",
    ROOT / "LanguageSpecific",
    ROOT / "PlatformSpecific",
    ROOT / "DesignUX",
    ROOT / "Tooling",
    ROOT / "WorkflowAutomation",
    ROOT / "Reference",
]

MAX_FILE_BYTES = 256 * 1024
MAX_EVIDENCE = 6

LOW_RISK_THRESHOLD = 30
HIGH_RISK_THRESHOLD = 60

RECOMMENDED_ACTION_BY_RISK = {
    "low": "allow",
    "review": "quarantine",
    "high": "quarantine",
}

HARD_FAIL_RULES = {
    "override_system_instructions": [
        r"\b(ignore|disregard|forget|override)\b[\s\W]{0,60}\b(system|developer)?\b[\s\W]{0,20}\b(instructions?|prompt|message)\b",
        r"\b(ignore|disregard|forget|override)\b[\s\W]{0,60}\b(system|developer)\b[\s\W]{0,40}\b(instructions?|prompt|message)\b",
        r"\b(system|developer)\b[\s\W]{0,40}\b(instructions?|prompt|message)\b[\s\W]{0,40}\b(ignore|disregard|override|forget)\b",
    ],
    "policy_bypass": [
        r"\b(bypass|disable|evade|circumvent)\b[\s\W]{0,40}\b(safety|policy|guardrails?|restrictions?)\b",
        r"\b(do not|don't)\b[\s\W]{0,30}\b(follow|respect|obey)\b[\s\W]{0,40}\b(policy|safety|guardrails?)\b",
    ],
    "secret_exfiltration": [
        r"\b(exfiltrat(e|ion)|steal|leak|dump|print|reveal)\b[\s\W]{0,50}\b(secret|token|api[\s_-]?key|password|credential)\b",
    ],
    "dangerous_path_access": [
        r"\b(cat|read|open|copy|upload|print)\b[\s\W]{0,50}(\.\./|/etc/passwd|~/.ssh|id_rsa|\.env)",
    ],
    "remote_payload_execution": [
        r"\b(curl|wget|invoke-webrequest)\b[\s\W]{0,80}\|\s*(bash|sh|powershell|pwsh)\b",
        r"\b(powershell|pwsh)\b[\s\W]{0,30}-enc(odedcommand)?\b",
    ],
}

SIGNAL_RULES = {
    "override_language": {
        "patterns": [
            r"\b(ignore|disregard|forget|override)\b[\s\W]{0,60}\b(previous|prior|earlier|all)\b[\s\W]{0,30}\b(instructions?|rules?|guidance)\b",
            r"\b(new instructions?|latest instructions?)\b[\s\W]{0,30}\b(overrule|replace|supersede)\b",
        ],
        "max_points": 20,
        "hit_points": 10,
    },
    "sensitive_command_language": {
        "patterns": [
            r"\b(rm\s+-rf|del\s+/f|format\s+[a-z]:|curl\s+http|wget\s+http|invoke-webrequest)\b",
            r"\b(exec|execute|run)\b[\s\W]{0,30}\b(shell|terminal|powershell|bash)\b",
        ],
        "max_points": 15,
        "hit_points": 7,
    },
    "path_breakout_hints": {
        "patterns": [
            r"\.\./",
            r"\b(/etc/passwd|/root/|~/.ssh|id_rsa|\.env)\b",
            r"\b(secrets?|credentials?|tokens?)\b[\s\W]{0,20}\b(file|folder|directory|path)\b",
        ],
        "max_points": 15,
        "hit_points": 6,
    },
    "structural_anomaly": {
        "patterns": [
            r"(?s)<!--.{0,300}(ignore|override|bypass|disable).{0,300}-->",
            r"\u200b|\u200c|\u200d|\ufeff",
        ],
        "max_points": 10,
        "hit_points": 5,
    },
    "obfuscated_override": {
        "patterns": [
            r"i\W*g\W*n\W*o\W*r\W*e[\s\W]{0,40}p\W*r\W*e\W*v\W*i\W*o\W*u\W*s",
        ],
        "max_points": 30,
        "hit_points": 30,
    },
}

ENCODED_KEYWORDS = ("ignore", "instructions", "system", "developer", "secret", "token", "password", "bypass")


@dataclass
class ScanFinding:
    skill_name: str
    skill_path: str
    risk_level: str
    score_total: int
    hard_fail: bool
    hard_fail_rules_triggered: list[str]
    signal_breakdown: dict[str, int]
    evidence_snippets: list[str]
    recommended_action: str
    confidence: str


@dataclass
class ScanOutcome:
    finding: ScanFinding
    final_action: str
    destination: str | None = None


def load_allowlist_phrases(path: Path = ALLOWLIST_FILE) -> list[str]:
    if not path.exists():
        return []

    phrases: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^-\s*(.+?)\s*$", line)
        if not match:
            continue
        value = match.group(1).strip().strip('"').strip("'").lower()
        if value:
            phrases.append(value)
    return phrases


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


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


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    freq: dict[str, int] = {}
    for char in value:
        freq[char] = freq.get(char, 0) + 1
    total = len(value)
    entropy = 0.0
    for count in freq.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def extract_snippet(text: str, start: int, end: int, context: int = 55) -> str:
    left = max(start - context, 0)
    right = min(end + context, len(text))
    snippet = text[left:right].replace("\n", " ")
    return re.sub(r"\s+", " ", snippet).strip()


def is_allowlisted(snippet: str, allowlist_phrases: Iterable[str]) -> bool:
    lowered = snippet.lower()
    return any(phrase in lowered for phrase in allowlist_phrases)


def find_pattern_hits(
    text: str,
    pattern_map: dict[str, list[str]],
    allowlist_phrases: Iterable[str],
    max_per_rule: int = 3,
) -> tuple[dict[str, int], list[str]]:
    counts: dict[str, int] = {}
    snippets: list[str] = []
    for rule_name, patterns in pattern_map.items():
        count = 0
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                snippet = extract_snippet(text, match.start(), match.end())
                if is_allowlisted(snippet, allowlist_phrases):
                    continue
                count += 1
                if len(snippets) < MAX_EVIDENCE:
                    snippets.append(f"{rule_name}: {snippet}")
                if count >= max_per_rule:
                    break
            if count >= max_per_rule:
                break
        if count > 0:
            counts[rule_name] = count
    return counts, snippets


def score_weighted_signals(
    text: str,
    allowlist_phrases: Iterable[str],
) -> tuple[dict[str, int], list[str]]:
    breakdown: dict[str, int] = {}
    snippets: list[str] = []
    for signal_name, config in SIGNAL_RULES.items():
        counts, signal_snippets = find_pattern_hits(
            text,
            {signal_name: config["patterns"]},
            allowlist_phrases,
        )
        hit_count = counts.get(signal_name, 0)
        if hit_count == 0:
            continue
        points = min(config["max_points"], hit_count * config["hit_points"])
        breakdown[signal_name] = points
        snippets.extend(signal_snippets)
    return breakdown, snippets


def detect_encoded_payload_signal(
    text: str,
    allowlist_phrases: Iterable[str],
) -> tuple[int, list[str]]:
    score = 0
    snippets: list[str] = []

    base64_candidates = re.findall(r"\b[A-Za-z0-9+/]{80,}={0,2}\b", text)
    for candidate in base64_candidates[:8]:
        if is_allowlisted(candidate, allowlist_phrases):
            continue
        try:
            decoded = base64.b64decode(candidate, validate=True)
            decoded_text = decoded.decode("utf-8", errors="ignore").lower()
        except Exception:
            decoded_text = ""
        if any(keyword in decoded_text for keyword in ENCODED_KEYWORDS):
            score = max(score, 30)
            snippets.append("encoded_payload: base64 payload decodes to suspicious instruction keywords.")
            continue

        entropy = shannon_entropy(candidate)
        if entropy < 3.7:
            continue

        if len(candidate) >= 140:
            score = max(score, 12)
            snippets.append("encoded_payload: high-entropy base64-like string present.")

    hex_candidates = re.findall(r"\b[0-9a-fA-F]{96,}\b", text)
    for candidate in hex_candidates[:6]:
        if is_allowlisted(candidate, allowlist_phrases):
            continue
        if shannon_entropy(candidate) >= 3.2:
            score = max(score, 10)
            snippets.append("encoded_payload: long high-entropy hex-like payload present.")
            break

    return score, snippets[:2]


def read_scannable_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    if path.stat().st_size > MAX_FILE_BYTES:
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def discover_related_files(skill_dir: Path) -> list[Path]:
    files: list[Path] = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        files.append(skill_md)

    for dirname in ("references", "scripts"):
        target = skill_dir / dirname
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {
                ".md",
                ".txt",
                ".rst",
                ".py",
                ".sh",
                ".ps1",
                ".json",
                ".yaml",
                ".yml",
                ".toml",
            }:
                continue
            files.append(path)
    return files[:40]


def compute_confidence(score_total: int, hard_fail: bool) -> str:
    if hard_fail or score_total >= 75:
        return "high"
    if score_total >= 40:
        return "medium"
    return "low"


def scan_skill_directory(skill_dir: Path, allowlist_phrases: list[str] | None = None) -> ScanFinding:
    allowlist = allowlist_phrases if allowlist_phrases is not None else load_allowlist_phrases()

    hard_fail_rules: set[str] = set()
    signal_breakdown: dict[str, int] = {}
    evidence_snippets: list[str] = []

    for file_path in discover_related_files(skill_dir):
        text = read_scannable_text(file_path)
        if not text:
            continue
        normalized = normalize_text(text)
        relative = display_path(file_path)

        hard_fail_counts, hard_snippets = find_pattern_hits(normalized, HARD_FAIL_RULES, allowlist)
        if hard_fail_counts:
            hard_fail_rules.update(hard_fail_counts.keys())
            for snippet in hard_snippets:
                if len(evidence_snippets) < MAX_EVIDENCE:
                    evidence_snippets.append(f"{relative}: {snippet}")

        weighted_scores, weighted_snippets = score_weighted_signals(normalized, allowlist)
        for key, points in weighted_scores.items():
            signal_breakdown[key] = signal_breakdown.get(key, 0) + points
        for snippet in weighted_snippets:
            if len(evidence_snippets) < MAX_EVIDENCE:
                evidence_snippets.append(f"{relative}: {snippet}")

        encoded_score, encoded_snippets = detect_encoded_payload_signal(normalized, allowlist)
        if encoded_score > 0:
            signal_breakdown["encoded_payload"] = signal_breakdown.get("encoded_payload", 0) + encoded_score
            for snippet in encoded_snippets:
                if len(evidence_snippets) < MAX_EVIDENCE:
                    evidence_snippets.append(f"{relative}: {snippet}")

    score_total = min(sum(signal_breakdown.values()), 100)
    hard_fail = len(hard_fail_rules) > 0
    effective_score = max(score_total, HIGH_RISK_THRESHOLD) if hard_fail else score_total

    if hard_fail or effective_score >= HIGH_RISK_THRESHOLD:
        risk_level = "high"
    elif effective_score >= LOW_RISK_THRESHOLD:
        risk_level = "review"
    else:
        risk_level = "low"

    recommended_action = RECOMMENDED_ACTION_BY_RISK[risk_level]
    confidence = compute_confidence(effective_score, hard_fail)

    return ScanFinding(
        skill_name=skill_dir.name,
        skill_path=display_path(skill_dir),
        risk_level=risk_level,
        score_total=effective_score,
        hard_fail=hard_fail,
        hard_fail_rules_triggered=sorted(hard_fail_rules),
        signal_breakdown=dict(sorted(signal_breakdown.items())),
        evidence_snippets=evidence_snippets[:MAX_EVIDENCE],
        recommended_action=recommended_action,
        confidence=confidence,
    )


def derive_skill_dirs_from_paths(paths: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for raw_path in paths:
        path = raw_path if raw_path.is_absolute() else (ROOT / raw_path)
        if not path.exists():
            continue

        if path.is_file():
            if path.name == "SKILL.md":
                found.add(path.parent.resolve())
                continue
            for parent in [path.parent, *path.parents]:
                if (parent / "SKILL.md").exists():
                    found.add(parent.resolve())
                    break
            continue

        if path.is_dir():
            if (path / "SKILL.md").exists():
                found.add(path.resolve())
                continue
            for skill_md in path.rglob("SKILL.md"):
                found.add(skill_md.parent.resolve())
    return sorted(found)


def discover_skill_dirs(mode: str, explicit_paths: list[Path] | None = None) -> list[Path]:
    if explicit_paths:
        return derive_skill_dirs_from_paths(explicit_paths)

    found: set[Path] = set()
    if mode == "intake":
        if not SKILLS_LOBBY.exists():
            return []
        for candidate in SKILLS_LOBBY.iterdir():
            if candidate.is_dir() and (candidate / "SKILL.md").exists():
                found.add(candidate.resolve())
        return sorted(found)

    for root in SWEEP_ROOTS:
        if not root.exists():
            continue
        for skill_md in root.rglob("SKILL.md"):
            found.add(skill_md.parent.resolve())
    return sorted(found)


def write_scan_findings_file(skill_dir: Path, finding: ScanFinding) -> None:
    payload = asdict(finding)
    payload["scanned_at_utc"] = datetime.now(timezone.utc).isoformat()
    target = skill_dir / ".scan-findings.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def quarantine_skill(skill_dir: Path, finding: ScanFinding, dry_run: bool) -> tuple[str, str | None]:
    destination = unique_destination(LIMBO_REVIEW / skill_dir.name)
    destination_relative = display_path(destination)
    if dry_run:
        return "would-quarantine", destination_relative

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(skill_dir), str(destination))
    write_scan_findings_file(destination, finding)
    return "quarantined", destination_relative


def build_outcome(
    finding: ScanFinding,
    skill_dir: Path,
    apply_quarantine: bool,
    dry_run: bool,
) -> ScanOutcome:
    if finding.recommended_action != "quarantine":
        return ScanOutcome(finding=finding, final_action="allow", destination=None)

    if not apply_quarantine:
        return ScanOutcome(finding=finding, final_action="report-only", destination=None)

    action, destination = quarantine_skill(skill_dir, finding, dry_run=dry_run)
    return ScanOutcome(finding=finding, final_action=action, destination=destination)


def render_report(outcomes: list[ScanOutcome], mode: str, dry_run: bool) -> str:
    header = "# Prompt Injection Sweep Report"
    if not outcomes:
        return (
            f"{header}\n\nMode: `{mode}`\nDry-run: `{str(dry_run).lower()}`\n\nNo skill folders were scanned."
        )

    lines = [
        header,
        "",
        f"Mode: `{mode}`",
        f"Dry-run: `{str(dry_run).lower()}`",
        "",
        f"Thresholds: review >= `{LOW_RISK_THRESHOLD}`, high >= `{HIGH_RISK_THRESHOLD}` or hard-fail.",
        "",
        "| Skill | Risk | Score | Hard Fail | Action | Destination | Evidence |",
        "|---|---|---:|---|---|---|---|",
    ]
    for outcome in outcomes:
        finding = outcome.finding
        evidence = finding.evidence_snippets[0] if finding.evidence_snippets else "None"
        lines.append(
            f"| `{escape_cell(finding.skill_name)}` | {escape_cell(finding.risk_level)} | "
            f"{finding.score_total} | {str(finding.hard_fail).lower()} | "
            f"{escape_cell(outcome.final_action)} | `{escape_cell(outcome.destination or '-')}` | "
            f"{escape_cell(evidence)} |"
        )
    return "\n".join(lines)


def serialize_outcomes(outcomes: list[ScanOutcome]) -> dict[str, object]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total": len(outcomes),
        "outcomes": [
            {
                "finding": asdict(item.finding),
                "final_action": item.final_action,
                "destination": item.destination,
            }
            for item in outcomes
        ],
    }


def read_paths_file(path: Path | None) -> list[Path]:
    if path is None or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    paths = [Path(line.strip()) for line in lines if line.strip()]
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt injection scanner for skill repositories.")
    parser.add_argument("--mode", choices=("intake", "sweep"), default="intake")
    parser.add_argument("--paths", nargs="*", default=[], help="Optional file/dir paths to scope scanning.")
    parser.add_argument("--paths-file", type=str, help="Optional text file with one path per line.")
    parser.add_argument("--dry-run", action="store_true", help="Do not mutate files when quarantine is enabled.")
    parser.add_argument(
        "--apply-quarantine",
        action="store_true",
        help="Move risky skills into Limbo/NeedsHumanReview.",
    )
    parser.add_argument("--report-file", type=str, help="Optional markdown report output path.")
    parser.add_argument("--findings-json", type=str, help="Optional JSON findings output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    explicit_paths = [Path(p) for p in args.paths]
    explicit_paths.extend(read_paths_file(Path(args.paths_file) if args.paths_file else None))

    allowlist_phrases = load_allowlist_phrases()
    skill_dirs = discover_skill_dirs(args.mode, explicit_paths=explicit_paths if explicit_paths else None)

    outcomes: list[ScanOutcome] = []
    for skill_dir in skill_dirs:
        finding = scan_skill_directory(skill_dir, allowlist_phrases=allowlist_phrases)
        outcome = build_outcome(
            finding=finding,
            skill_dir=skill_dir,
            apply_quarantine=args.apply_quarantine,
            dry_run=args.dry_run,
        )
        outcomes.append(outcome)

    report = render_report(outcomes, mode=args.mode, dry_run=args.dry_run)
    print(report)

    if args.report_file:
        report_path = Path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")

    payload = serialize_outcomes(outcomes)
    if args.findings_json:
        findings_path = Path(args.findings_json)
        findings_path.parent.mkdir(parents=True, exist_ok=True)
        findings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if any(item.finding.recommended_action == "quarantine" for item in outcomes):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
