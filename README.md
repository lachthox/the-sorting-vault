# Codex Skills Hub

Central repository for reusable skills and playbooks.

## Folder Structure

- `BestPractices/` - Cross-cutting engineering standards, checklists, and quality guides.
- `LanguageSpecific/` - Skills tied to a programming language or runtime.
- `PlatformSpecific/` - Operating-system-specific skills.
  - `Linux/`
  - `Windows/`
  - `macOS/`
- `DesignUX/` - UI/UX, accessibility, and product interaction design guidance.
- `Tooling/` - IDE, CLI, CI/CD, and infrastructure tool workflows.
- `WorkflowAutomation/` - Repeatable automation flows and agent-assisted pipelines.
- `Reference/` - Shared templates, snippets, examples, and glossary material.
- `SkillsLobby/` - Intake folder for new uploads that should be auto-routed by GitHub Actions.

## Suggested Skill Layout

Each skill folder can follow:

- `SKILL.md` - Main instructions and workflow.
- `assets/` - Supporting static files and templates.
- `scripts/` - Utility scripts for setup or execution.
- `references/` - Optional deep reference docs.

## Naming Conventions

- Use `PascalCase` for top-level categories.
- Use concise, descriptive skill names.
- Keep one skill per folder.

## Auto Routing

Push new skill folders into `SkillsLobby/` and the `Skill Router` workflow will move each folder into the best match.

Routing order:

- Explicit `Category: <value>` in `SKILL.md` (preferred).
- Keyword-based classification from folder name + `SKILL.md` contents.
- Fallback to `Reference/Unsorted/` when no strong match is found.

Report behavior:

- On pull requests, the workflow posts/updates a comment showing exactly why each skill was routed.
- On pushes to `main`, the workflow applies the move and writes the same routing report to the run summary.

Supported explicit categories:

- `BestPractices`
- `LanguageSpecific`
- `Linux`
- `Windows`
- `macOS`
- `DesignUX`
- `Tooling`
- `WorkflowAutomation`
- `Reference`
