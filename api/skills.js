const fs = require("fs");
const path = require("path");

const ROOT_DIR = process.cwd();
const TAXONOMY_ROOTS = [
  { directory: "BestPractices", label: "BestPractices" },
  { directory: "LanguageSpecific", label: "LanguageSpecific" },
  { directory: path.join("PlatformSpecific", "Linux"), label: "PlatformSpecific/Linux" },
  { directory: path.join("PlatformSpecific", "Windows"), label: "PlatformSpecific/Windows" },
  { directory: path.join("PlatformSpecific", "macOS"), label: "PlatformSpecific/macOS" },
  { directory: "DesignUX", label: "DesignUX" },
  { directory: "Tooling", label: "Tooling" },
  { directory: "WorkflowAutomation", label: "WorkflowAutomation" },
  { directory: "Reference", label: "Reference" },
];

function safeReadDir(directory) {
  try {
    return fs.readdirSync(directory, { withFileTypes: true });
  } catch (error) {
    return [];
  }
}

function parseFrontmatter(content) {
  const frontmatterMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  const metadata = {};
  let body = content;

  if (frontmatterMatch) {
    const lines = frontmatterMatch[1].split(/\r?\n/);
    let currentKey = null;

    for (const line of lines) {
      const match = line.match(/^([A-Za-z0-9_-]+)\s*:\s*(.+)$/);
      if (match) {
        const key = match[1].toLowerCase();
        const value = match[2].trim().replace(/^['"]|['"]$/g, "");
        metadata[key] = value;
        currentKey = key;
        continue;
      }

      if (!currentKey) {
        continue;
      }

      if (/^\s+/.test(line)) {
        const continuation = line.trim();
        if (continuation) {
          metadata[currentKey] = `${metadata[currentKey]} ${continuation}`.trim();
        }
      }
    }
    body = content.slice(frontmatterMatch[0].length);
  }

  return { metadata, body };
}

function getBodyPreview(body) {
  const lines = body
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));

  const preview = lines.slice(0, 2).join(" ");
  if (preview.length <= 200) {
    return preview;
  }
  return `${preview.slice(0, 197)}...`;
}

function findSkillFolders(rootDirectory) {
  const discovered = [];
  const stack = [rootDirectory];

  while (stack.length > 0) {
    const currentDir = stack.pop();
    const entries = safeReadDir(currentDir);
    const hasSkillFile = entries.some((entry) => entry.isFile() && entry.name === "SKILL.md");

    if (hasSkillFile && currentDir !== rootDirectory) {
      discovered.push(currentDir);
      continue;
    }

    for (const entry of entries) {
      if (!entry.isDirectory()) {
        continue;
      }
      if (entry.name.startsWith(".")) {
        continue;
      }
      stack.push(path.join(currentDir, entry.name));
    }
  }

  return discovered;
}

function buildSkillRecord(skillDirectory, categoryLabel) {
  const skillFilePath = path.join(skillDirectory, "SKILL.md");
  const rawContent = fs.readFileSync(skillFilePath, "utf8");
  const { metadata, body } = parseFrontmatter(rawContent);
  const relativeDirectory = path.relative(ROOT_DIR, skillDirectory).replace(/\\/g, "/");
  const relativeSkillFile = path.relative(ROOT_DIR, skillFilePath).replace(/\\/g, "/");

  return {
    name: metadata.name || path.basename(skillDirectory),
    description: metadata.description || getBodyPreview(body) || "No description provided.",
    category: categoryLabel,
    declaredCategory: metadata.category || null,
    folderPath: relativeDirectory,
    skillFilePath: relativeSkillFile,
    hasAssets: fs.existsSync(path.join(skillDirectory, "assets")),
    hasScripts: fs.existsSync(path.join(skillDirectory, "scripts")),
    hasReferences: fs.existsSync(path.join(skillDirectory, "references")),
  };
}

function collectSkills() {
  const skills = [];

  for (const taxonomyRoot of TAXONOMY_ROOTS) {
    const absoluteRoot = path.join(ROOT_DIR, taxonomyRoot.directory);
    if (!fs.existsSync(absoluteRoot)) {
      continue;
    }

    for (const skillDirectory of findSkillFolders(absoluteRoot)) {
      try {
        skills.push(buildSkillRecord(skillDirectory, taxonomyRoot.label));
      } catch (error) {
        continue;
      }
    }
  }

  return skills.sort((a, b) => {
    const categoryCompare = a.category.localeCompare(b.category);
    if (categoryCompare !== 0) {
      return categoryCompare;
    }
    return a.name.localeCompare(b.name);
  });
}

function handler(req, res) {
  try {
    const skills = collectSkills();
    res.status(200).json({
      generatedAt: new Date().toISOString(),
      total: skills.length,
      skills,
    });
  } catch (error) {
    res.status(500).json({
      error: "Failed to load routed skills.",
    });
  }
}

module.exports = handler;
module.exports.collectSkills = collectSkills;
