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
- `Limbo/NeedsHumanReview/` - Holding area for skills that fail quality checks and require manual approval.

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

- Quality gate runs first (worthiness check).
- Explicit `Category: <value>` in `SKILL.md` (preferred).
- Keyword-based classification from folder name + `SKILL.md` contents.
- Fallback to `Reference/Unsorted/` when no strong match is found.

Report behavior:

- On pull requests, the workflow posts/updates a comment showing exactly why each skill was routed.
- On pushes to `main`, the workflow applies the move and writes the same routing report to the run summary.

## Worthiness Gate Criteria

A skill in `SkillsLobby/` is scored out of 100 before sorting.

Core checks:

- `SKILL.md` must exist.
- YAML frontmatter must be first and valid (`---` ... `---`).
- Frontmatter must include non-empty `name` and `description`.
- Description should include trigger context (for example `Use when ...`).
- Body should include real guidance (not just stubs), with at least one `#` and one `##` heading.
- Very long `SKILL.md` files are penalized to encourage progressive disclosure.
- If `scripts/`, `references/`, or `assets/` folders exist, SKILL.md should mention them.

Decision:

- Score `>= 70` with no hard-fail conditions: skill is considered worthy and gets sorted.
- Otherwise: skill is moved to `Limbo/NeedsHumanReview/` until a human approves.

Manual approval flow:

- To approve a limbo skill, move it back into `SkillsLobby/` and push.
- To reject a limbo skill, remove it from `Limbo/NeedsHumanReview/`.

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
