const state = {
  skills: [],
  filteredSkills: [],
  selectedCategory: "",
  query: "",
  generatedAt: "",
};

const elements = {
  totalSkills: document.getElementById("totalSkills"),
  totalCategories: document.getElementById("totalCategories"),
  generatedAt: document.getElementById("generatedAt"),
  feedback: document.getElementById("feedback"),
  grid: document.getElementById("grid"),
  searchInput: document.getElementById("searchInput"),
  categorySelect: document.getElementById("categorySelect"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatGeneratedAt(value) {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) {
    return "-";
  }
  return parsed.toLocaleString();
}

function updateCategoryOptions() {
  const categories = Array.from(new Set(state.skills.map((skill) => skill.category))).sort((a, b) =>
    a.localeCompare(b)
  );

  const existingValue = elements.categorySelect.value;
  elements.categorySelect.innerHTML = '<option value="">All categories</option>';

  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    elements.categorySelect.append(option);
  }

  elements.categorySelect.value = categories.includes(existingValue) ? existingValue : "";
  state.selectedCategory = elements.categorySelect.value;
}

function applyFilters() {
  const normalizedQuery = state.query.trim().toLowerCase();
  state.filteredSkills = state.skills.filter((skill) => {
    if (state.selectedCategory && skill.category !== state.selectedCategory) {
      return false;
    }

    if (!normalizedQuery) {
      return true;
    }

    const haystack = `${skill.name} ${skill.description} ${skill.folderPath}`.toLowerCase();
    return haystack.includes(normalizedQuery);
  });
}

function renderStats(generatedAt) {
  const categories = new Set(state.skills.map((skill) => skill.category));
  elements.totalSkills.textContent = String(state.skills.length);
  elements.totalCategories.textContent = String(categories.size);
  elements.generatedAt.textContent = formatGeneratedAt(generatedAt);
}

function resourcePills(skill) {
  const pills = [];
  if (skill.hasAssets) {
    pills.push("assets");
  }
  if (skill.hasScripts) {
    pills.push("scripts");
  }
  if (skill.hasReferences) {
    pills.push("references");
  }
  if (pills.length === 0) {
    pills.push("single-file");
  }
  return pills
    .map((pill) => `<span class="resource-pill">${escapeHtml(pill)}</span>`)
    .join("");
}

function renderGrid() {
  if (state.filteredSkills.length === 0) {
    elements.feedback.textContent = "No skills match the current filters.";
    elements.grid.innerHTML = "";
    return;
  }

  elements.feedback.textContent = `${state.filteredSkills.length} skill(s) visible`;
  elements.grid.innerHTML = state.filteredSkills
    .map(
      (skill, index) => `
      <article class="skill-card" style="animation-delay: ${Math.min(index * 30, 240)}ms">
        <div class="skill-head">
          <h2 class="skill-title">${escapeHtml(skill.name)}</h2>
          <span class="category-chip">${escapeHtml(skill.category)}</span>
        </div>
        <p class="skill-description">${escapeHtml(skill.description)}</p>
        <p class="skill-path">${escapeHtml(skill.folderPath)}</p>
        <div class="resource-row">${resourcePills(skill)}</div>
      </article>
    `
    )
    .join("");
}

function refreshView() {
  applyFilters();
  renderStats(state.generatedAt);
  renderGrid();
}

async function loadSkills() {
  elements.feedback.textContent = "Loading routed skills...";

  const response = await fetch("/api/skills");
  if (!response.ok) {
    throw new Error("Request failed");
  }

  const payload = await response.json();
  state.skills = Array.isArray(payload.skills) ? payload.skills : [];
  state.generatedAt = payload.generatedAt || "";
  updateCategoryOptions();
  refreshView();
}

elements.searchInput.addEventListener("input", (event) => {
  state.query = event.target.value || "";
  refreshView();
});

elements.categorySelect.addEventListener("change", (event) => {
  state.selectedCategory = event.target.value || "";
  refreshView();
});

loadSkills().catch(() => {
  elements.feedback.textContent = "Could not load skills from /api/skills.";
  elements.totalSkills.textContent = "0";
  elements.totalCategories.textContent = "0";
});
