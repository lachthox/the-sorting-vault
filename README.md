# The Sorting Vault

A centralized repository for reusable skills, playbooks, and development guidelines. This vault automatically organizes, validates, and secures your team's knowledge base using intelligent routing and security scanning.

## 🏷️ Topics

`skills` · `playbooks` · `knowledge-base` · `automation` · `best-practices` · `workflow-automation` · `skill-library` · `reusable-components` · `github-actions` · `ci-cd` · `security-scanning`

## 📖 Table of Contents

- [Quick Start](#-quick-start)
- [Folder Structure](#-folder-structure)
- [Using Skills](#-using-skills)
- [Contributing Skills](#-contributing-skills)
- [Advanced Topics](#-advanced-topics)
  - [Auto Routing](#auto-routing)
  - [Prompt Injection Sweeping](#prompt-injection-sweeping)
  - [Worthiness Gate Criteria](#worthiness-gate-criteria)
  - [Import Skills From Other Repositories](#import-skills-from-other-repositories)

---

## 🚀 Quick Start

**To use an existing skill:**
1. Browse the category folders below to find relevant skills
2. Each skill has a `SKILL.md` with step-by-step instructions
3. Follow the workflow described in the skill document

**To contribute a new skill:**
1. Create your skill folder with a `SKILL.md` file (see [Suggested Skill Layout](#suggested-skill-layout))
2. Push it to the `SkillsLobby/` folder
3. GitHub Actions will automatically validate, secure, and route it to the appropriate category

---

## 📁 Folder Structure

### Organized Skills

- **`BestPractices/`** - Cross-cutting engineering standards, checklists, and quality guides
- **`LanguageSpecific/`** - Skills tied to a programming language or runtime
- **`PlatformSpecific/`** - Operating-system-specific skills
  - `Linux/`
  - `Windows/`
  - `macOS/`
- **`DesignUX/`** - UI/UX, accessibility, and product interaction design guidance
- **`Tooling/`** - IDE, CLI, CI/CD, and infrastructure tool workflows
- **`WorkflowAutomation/`** - Repeatable automation flows and agent-assisted pipelines
- **`Reference/`** - Shared templates, snippets, examples, and glossary material

### Special Folders

- **`SkillsLobby/`** - Intake folder for new skill uploads (auto-routed by GitHub Actions)
- **`Limbo/NeedsHumanReview/`** - Holding area for skills that need manual review

---

## 📝 Using Skills

### Suggested Skill Layout

Each skill folder follows this structure:

- **`SKILL.md`** - Main instructions and workflow (required)
- **`assets/`** - Supporting static files and templates (optional)
- **`scripts/`** - Utility scripts for setup or execution (optional)
- **`references/`** - Deep reference documentation (optional)

### Naming Conventions

- Use **`PascalCase`** for top-level category folders
- Use **concise, descriptive names** for skill folders
- Keep **one skill per folder**

---

## 🤝 Contributing Skills

### How to Add a New Skill

1. **Create your skill folder** in `SkillsLobby/` with a `SKILL.md` file
2. **Include YAML frontmatter** with `name`, `description`, and optional `Category`
3. **Push to main** - GitHub Actions handles the rest!

The automated workflow will:
- ✅ Run security scans to detect prompt injection attempts
- ✅ Validate quality using the worthiness gate
- ✅ Route your skill to the appropriate category folder
- ✅ Post a detailed report explaining routing decisions

### Supported Explicit Categories

Specify a category in your `SKILL.md` frontmatter to skip keyword-based classification:

```yaml
---
name: Your Skill Name
description: Use when you need to...
Category: BestPractices
---
```

Available categories:
- `BestPractices`
- `LanguageSpecific`
- `Linux`, `Windows`, `macOS` (under PlatformSpecific)
- `DesignUX`
- `Tooling`
- `WorkflowAutomation`
- `Reference`

---

## 🔧 Advanced Topics

### Auto Routing

Push new skill folders into `SkillsLobby/` and the **Skill Router** workflow automatically moves each folder to its best category match.

**Routing order:**

1. **Prompt-injection security gate** runs first
2. **Quality gate** runs second (worthiness check)
3. **Explicit `Category: <value>`** in `SKILL.md` (preferred)
4. **Keyword-based classification** from folder name + `SKILL.md` contents
5. **Fallback** to `Reference/Unsorted/` when no strong match is found

**Report behavior:**

- **On pull requests:** The workflow posts/updates a comment showing exactly why each skill was routed
- **On pushes to `main`:** The workflow applies the move and writes the routing report to the run summary

### Prompt Injection Sweeping

The repository uses a Python-only scanner (`.github/scripts/prompt_injection_scan.py`) with no LLM dependency to protect against malicious content.

**Where it runs:**

- **Intake:** Every skill in `SkillsLobby/` before sorting
- **On-change sweep:** When sorted skills are modified on `main`
- **Scheduled sweep:** Nightly scan across all sorted skills
- **PR sweep:** Dry-run security report comment for changed sorted skills

**Risk levels:**

- **`low`** (`score < 30`) → Allowed
- **`review`** (`30 ≤ score < 60`) → Quarantined to limbo
- **`high`** (`score ≥ 60` or hard-fail rule) → Quarantined to limbo

**What gets flagged:**

- Instruction override / policy bypass language
- Secret exfiltration cues
- Dangerous path breakout attempts
- Encoded payload indicators
- Structural anomaly signals (hidden or obfuscated instruction content)

**Allowlist:** Safe false-positive phrases can be tuned in `.github/security/scan_allowlist.yml`

### Worthiness Gate Criteria

A skill in `SkillsLobby/` is scored out of 100 before sorting to ensure quality.

**Core checks:**

- ✅ `SKILL.md` must exist
- ✅ YAML frontmatter must be first and valid (`---` ... `---`)
- ✅ Frontmatter must include non-empty `name` and `description`
- ✅ Description should include trigger context (e.g., `Use when ...`)
- ✅ Body should include real guidance (not just stubs), with at least one `#` and one `##` heading
- ⚠️ Very long `SKILL.md` files are penalized to encourage progressive disclosure
- ✅ If `scripts/`, `references/`, or `assets/` folders exist, `SKILL.md` should mention them

**Decision:**

- **Score ≥ 70** with no hard-fail conditions → Skill is worthy and gets sorted
- **Otherwise** → Skill is moved to `Limbo/NeedsHumanReview/` until a human approves

**Manual approval flow:**

- To **approve** a limbo skill: Remediate issues, move it back to `SkillsLobby/`, and push
- To **reject** a limbo skill: Remove it from `Limbo/NeedsHumanReview/`
- Security-quarantined skills include `.scan-findings.json` for reviewer context

### Import Skills From Other Repositories

Use the importer CLI to ingest skills that contain either `SKILL.md` or `SKILLS.md`. Imported folders are copied into `SkillsLobby/`, then passed through the same security + quality + routing flow.

**Examples:**

```bash
# Import from a local repo path and apply routing
python .github/scripts/import_skill_repos.py C:\path\to\skills-repo

# Import from multiple sources, but preview routing only
python .github/scripts/import_skill_repos.py https://github.com/org/repo-a.git https://github.com/org/repo-b.git --route-dry-run

# Import only (skip routing)
python .github/scripts/import_skill_repos.py C:\path\to\skills-repo --skip-route
```

---

## 📄 License & Contributing

This repository is designed to be a collaborative knowledge base. Contributions are welcome! Please follow the guidelines above when adding new skills.

For more technical details about development, testing, and contributing code to the automation scripts, see [AGENTS.md](AGENTS.md).
