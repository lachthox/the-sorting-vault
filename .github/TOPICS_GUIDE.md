# How to Add Repository Topics

Repository topics help users discover this project on GitHub. The recommended topics are stored in `topics.txt`.

## Adding Topics via GitHub UI

1. Go to the repository page: https://github.com/lachthox/the-sorting-vault
2. Click the ⚙️ gear icon next to "About" on the right sidebar
3. In the "Topics" field, add the topics from `.github/topics.txt`:
   - skills
   - playbooks
   - knowledge-base
   - automation
   - best-practices
   - workflow-automation
   - skill-library
   - reusable-components
   - github-actions
   - ci-cd
   - security-scanning
   - prompt-injection
   - skill-routing
   - development-guidelines
   - engineering-standards

4. Click "Save changes"

## Adding Topics via GitHub API

You can also add topics programmatically using the GitHub API:

```bash
# Replace YOUR_TOKEN with a personal access token
curl -X PUT \
  -H "Accept: application/vnd.github.mercy-preview+json" \
  -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/lachthox/the-sorting-vault/topics \
  -d '{
    "names": [
      "skills",
      "playbooks", 
      "knowledge-base",
      "automation",
      "best-practices",
      "workflow-automation",
      "skill-library",
      "reusable-components",
      "github-actions",
      "ci-cd",
      "security-scanning",
      "prompt-injection",
      "skill-routing",
      "development-guidelines",
      "engineering-standards"
    ]
  }'
```

## Why These Topics?

These topics were chosen to help potential users find this repository when searching for:
- **Skills & playbooks** - Core functionality of the vault
- **Knowledge management** - Central knowledge base concept
- **Automation** - Auto-routing and workflow features
- **Best practices** - Engineering standards content
- **GitHub Actions & CI/CD** - Implementation technology
- **Security** - Prompt injection scanning feature
- **Development guidelines** - Content type stored in vault
