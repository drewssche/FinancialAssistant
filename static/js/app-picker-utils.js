(() => {
  const DEFAULT_CATEGORY_USAGE_KEY = "fa_category_usage_v1";

  function readUsageMap(storageKey = DEFAULT_CATEGORY_USAGE_KEY) {
    try {
      const raw = localStorage.getItem(storageKey);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  function sortCategoriesByUsage(categories, query = "", storageKey = DEFAULT_CATEGORY_USAGE_KEY) {
    const usage = readUsageMap(storageKey);
    const normalizedQuery = String(query || "").trim().toLowerCase();
    return (categories || [])
      .filter((item) => {
        if (!normalizedQuery) {
          return true;
        }
        return item.name.toLowerCase().includes(normalizedQuery) || (item.group_name || "").toLowerCase().includes(normalizedQuery);
      })
      .map((item) => ({ ...item, usage: Number(usage[String(item.id)] || 0) }))
      .sort((a, b) => {
        if (b.usage !== a.usage) {
          return b.usage - a.usage;
        }
        const colorA = (a.group_accent_color || "~").toLowerCase();
        const colorB = (b.group_accent_color || "~").toLowerCase();
        if (colorA !== colorB) {
          return colorA.localeCompare(colorB, "ru");
        }
        const groupA = (a.group_name || "~").toLowerCase();
        const groupB = (b.group_name || "~").toLowerCase();
        if (groupA !== groupB) {
          return groupA.localeCompare(groupB, "ru");
        }
        return a.name.localeCompare(b.name, "ru");
      });
  }

  function createChipButton({ datasetName, datasetValue = "", selected = false, html = "", className = "chip-btn" } = {}) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = className;
    if (selected) {
      btn.classList.add("active");
    }
    if (datasetName) {
      btn.dataset[datasetName] = String(datasetValue ?? "");
    }
    btn.innerHTML = html;
    return btn;
  }

  function createMetaChipButton({ datasetName, datasetValue = "", selected = false, label = "", core } = {}) {
    return createChipButton({
      datasetName,
      datasetValue,
      selected,
      className: "chip-btn chip-btn-meta",
      html: core.renderMetaChip(label),
    });
  }

  function createActionChipButton({ datasetName, datasetValue = "", label = "" } = {}) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip-btn chip-btn-create";
    if (datasetName) {
      btn.dataset[datasetName] = String(datasetValue ?? "");
    }
    btn.textContent = label;
    return btn;
  }

  window.App = window.App || {};
  window.App.pickerUtils = {
    DEFAULT_CATEGORY_USAGE_KEY,
    readUsageMap,
    sortCategoriesByUsage,
    createChipButton,
    createMetaChipButton,
    createActionChipButton,
  };
})();
