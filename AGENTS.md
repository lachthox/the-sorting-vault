# Repository Guidelines

## Project Structure & Module Organization
This repository stores reusable skills and routes them into taxonomy folders:
`BestPractices/`, `LanguageSpecific/`, `PlatformSpecific/` (`Linux/`, `Windows/`, `macOS/`), `DesignUX/`, `Tooling/`, `WorkflowAutomation/`, and `Reference/`.

New submissions land in `SkillsLobby/`. Skills that fail security or quality checks are quarantined to `Limbo/NeedsHumanReview/`.

Automation code lives in `.github/scripts/`:
- `route_skills.py` gates and routes skills.
- `prompt_injection_scan.py` performs intake/sweep security scanning.
- Tests and fixtures are in `.github/scripts/tests/`.

## Build, Test, and Development Commands
Use Python 3.12 (matches CI workflows).

- `python -m unittest discover .github/scripts/tests -v`  
  Run all scanner tests.
- `python .github/scripts/route_skills.py --dry-run --report-file routing-report.md`  
  Preview routing decisions without moving folders.
- `python .github/scripts/route_skills.py --report-file routing-report.md`  
  Apply routing for skills in `SkillsLobby/`.
- `python .github/scripts/prompt_injection_scan.py --mode intake --dry-run --report-file scan-report.md`  
  Run intake security scan locally.

## Coding Style & Naming Conventions
Python code follows PEP 8 conventions: 4-space indentation, clear function names, and type hints for non-trivial interfaces. Prefer `pathlib.Path`, `dataclass`, and small pure functions.

Repository naming conventions:
- Top-level category folders use `PascalCase`.
- One skill per folder, with a required `SKILL.md`.
- Optional `assets/`, `scripts/`, and `references/` directories should be explicitly mentioned in `SKILL.md`.

## Testing Guidelines
Tests use `unittest` with names matching `test_*.py` and methods named `test_*`.
When adding detection or routing logic, add focused fixtures under `.github/scripts/tests/fixtures/` and assert risk, score, and action outcomes.

## Commit & Pull Request Guidelines
Recent history favors short, imperative commit subjects (for example: `Add skill worthiness gate and limbo queue`, `Harden prompt-injection scanner ...`).

For pull requests:
- Summarize behavior changes and affected paths.
- Link the related issue when available.
- Include dry-run/report output snippets when changing routing or scanner logic.
- Mention any manual follow-up needed for `Limbo/NeedsHumanReview/`.
