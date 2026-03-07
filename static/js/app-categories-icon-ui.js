(() => {
  const { el } = window.App;

  const CATEGORY_ICON_POOL = [
    "🍽️",
    "🍔",
    "🥐",
    "🍞",
    "🥩",
    "🍣",
    "🍰",
    "🍺",
    "🍷",
    "☕",
    "🫖",
    "🏠",
    "🛋️",
    "🪑",
    "🪴",
    "🧹",
    "🧺",
    "🚬",
    "🚭",
    "🪒",
    "🧴",
    "🧼",
    "🪥",
    "🚕",
    "🚇",
    "🚌",
    "🚗",
    "🚙",
    "🛵",
    "🚲",
    "⛽",
    "🅿️",
    "🛒",
    "🏪",
    "🏬",
    "🛍️",
    "🍎",
    "🥗",
    "🍕",
    "🥤",
    "💊",
    "🏥",
    "🦷",
    "🩺",
    "🧘",
    "💇",
    "💅",
    "🎓",
    "📚",
    "💼",
    "💻",
    "🖥️",
    "⌚",
    "🎧",
    "🎮",
    "🎬",
    "🎵",
    "⚽",
    "🏋️",
    "🎨",
    "🎁",
    "💡",
    "📱",
    "📺",
    "📶",
    "🛠️",
    "🧾",
    "💰",
    "💵",
    "💶",
    "💸",
    "🪙",
    "💎",
    "📈",
    "📉",
    "🏦",
    "💳",
    "💷",
    "🧮",
    "🧠",
    "🧳",
    "✈️",
    "🚆",
    "🚢",
    "🏨",
    "🐾",
    "👶",
    "🧸",
    "🔧",
    "📦",
    "📬",
    "🔌",
    "🔒",
    "🌐",
    "📣",
    "❤️",
    "🙏",
  ];

  function updateIconToggleLabel(toggleNode, iconValue) {
    if (!toggleNode) {
      return;
    }
    toggleNode.textContent = iconValue || "+";
  }

  function closeIconPopovers() {
    el.categoryIconPopover.classList.add("hidden");
    el.editCategoryIconPopover.classList.add("hidden");
  }

  function bindIconPopoverOnce(popoverNode) {
    if (!popoverNode || popoverNode.dataset.boundClick === "1") {
      return;
    }
    popoverNode.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-icon]");
      if (!btn) {
        return;
      }
      const hiddenId = popoverNode.dataset.hiddenTarget;
      const toggleId = popoverNode.dataset.toggleTarget;
      const hiddenNode = hiddenId ? document.getElementById(hiddenId) : null;
      const toggleNode = toggleId ? document.getElementById(toggleId) : null;
      if (!hiddenNode) {
        return;
      }
      hiddenNode.value = btn.dataset.icon || "";
      for (const option of popoverNode.querySelectorAll(".icon-option")) {
        option.classList.toggle("active", option === btn);
      }
      updateIconToggleLabel(toggleNode, hiddenNode.value);
      popoverNode.classList.add("hidden");
    });
    popoverNode.dataset.boundClick = "1";
  }

  function renderIconPopover(popoverNode, hiddenNode, toggleNode) {
    if (!popoverNode || !hiddenNode || !toggleNode) {
      return;
    }
    popoverNode.dataset.hiddenTarget = hiddenNode.id || "";
    popoverNode.dataset.toggleTarget = toggleNode.id || "";
    bindIconPopoverOnce(popoverNode);
    popoverNode.innerHTML = "";
    const emptyButton = document.createElement("button");
    emptyButton.type = "button";
    emptyButton.className = "icon-option icon-option-empty";
    emptyButton.dataset.icon = "";
    emptyButton.textContent = "∅";
    emptyButton.title = "Без иконки";
    if (!hiddenNode.value) {
      emptyButton.classList.add("active");
    }
    popoverNode.appendChild(emptyButton);
    for (const icon of CATEGORY_ICON_POOL) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "icon-option";
      button.dataset.icon = icon;
      button.textContent = icon;
      if (hiddenNode.value === icon) {
        button.classList.add("active");
      }
      popoverNode.appendChild(button);
    }
  }

  function setupCategoryIconPickers() {
    renderIconPopover(el.categoryIconPopover, el.categoryIcon, el.categoryIconToggle);
    renderIconPopover(el.editCategoryIconPopover, el.editCategoryIcon, el.editCategoryIconToggle);
    updateIconToggleLabel(el.categoryIconToggle, el.categoryIcon.value);
    updateIconToggleLabel(el.editCategoryIconToggle, el.editCategoryIcon.value);
  }

  window.App.categoryIconUi = {
    updateIconToggleLabel,
    closeIconPopovers,
    setupCategoryIconPickers,
  };
})();
