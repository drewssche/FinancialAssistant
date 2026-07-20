(() => {
  const { el } = window.App;
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils") || window.App.pickerUtils;

  const CATEGORY_ICON_GROUPS = [
    { label: "Еда и напитки", icons: ["🍽️", "🍔", "🥐", "🍞", "🥩", "🍣", "🍰", "🍎", "🥗", "🍕", "🥤", "☕", "🫖", "🍺", "🍷", "🔥"] },
    { label: "Дом и счета", icons: ["🏠", "🛋️", "🪑", "🪴", "🧹", "🧺", "💡", "🚿", "🔌", "📱", "📺", "📶", "🌐", "🔁", "🧾", "⚠️"] },
    { label: "Покупки и уход", icons: ["🛒", "🏪", "🏬", "🛍️", "👕", "👟", "📦", "💊", "🏥", "🦷", "🩺", "🧘", "💇", "💅", "🪒", "🧴", "🧼", "🪥", "🚬", "🚭"] },
    { label: "Транспорт и поездки", icons: ["🚕", "🚇", "🚌", "🚗", "🚙", "🛵", "🚲", "⛽", "🅿️", "🔑", "🧳", "✈️", "🚆", "🚢", "🏨"] },
    { label: "Работа и развитие", icons: ["💼", "💻", "🖥️", "🎓", "📚", "🧠", "🛠️", "🔧", "📣", "👥"] },
    { label: "Досуг и события", icons: ["⌚", "🎧", "🎮", "🎬", "🎵", "⚽", "🏋️", "🎨", "🎯", "🎁", "🎂", "❤️", "🙏", "🐾", "👶", "🧸"] },
    { label: "Финансы", icons: ["💰", "💵", "💶", "💷", "💸", "🪙", "💎", "📈", "📉", "🏦", "💳", "🧮", "↩️", "↔️", "⚖️"] },
    { label: "Прочее", icons: ["📬", "🔒", "🔎", "❗", "🚻"] },
  ];

  function updateIconToggleLabel(toggleNode, iconValue) {
    if (!toggleNode) {
      return;
    }
    toggleNode.textContent = iconValue || "+";
  }

  function closeIconPopovers() {
    if (pickerUtils?.setPopoverOpen) {
      pickerUtils.setPopoverOpen(el.categoryIconPopover, false, { owners: [el.categoryIconToggle].filter(Boolean) });
      pickerUtils.setPopoverOpen(el.editCategoryIconPopover, false, { owners: [el.editCategoryIconToggle].filter(Boolean) });
      return;
    }
    el.categoryIconPopover.classList.add("hidden");
    el.editCategoryIconPopover.classList.add("hidden");
  }

  function toggleIconPopover(mode = "create") {
    const isEdit = mode === "edit";
    const popoverNode = isEdit ? el.editCategoryIconPopover : el.categoryIconPopover;
    const toggleNode = isEdit ? el.editCategoryIconToggle : el.categoryIconToggle;
    const otherPopover = isEdit ? el.categoryIconPopover : el.editCategoryIconPopover;
    const otherToggle = isEdit ? el.categoryIconToggle : el.editCategoryIconToggle;
    if (!popoverNode || !toggleNode) {
      return;
    }
    const shouldOpen = popoverNode.classList.contains("hidden");
    if (pickerUtils?.setPopoverOpen) {
      pickerUtils.setPopoverOpen(otherPopover, false, { owners: [otherToggle].filter(Boolean) });
      pickerUtils.setPopoverOpen(popoverNode, shouldOpen, {
        owners: [toggleNode, toggleNode.closest(".icon-select")].filter(Boolean),
      });
      return;
    }
    otherPopover?.classList.add("hidden");
    popoverNode.classList.toggle("hidden", !shouldOpen);
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
    popoverNode.classList.add("app-popover-floating", "category-icon-popover");
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
    const emptyGroup = document.createElement("div");
    emptyGroup.className = "icon-option-grid";
    emptyGroup.appendChild(emptyButton);
    popoverNode.appendChild(emptyGroup);
    for (const groupConfig of CATEGORY_ICON_GROUPS) {
      const group = document.createElement("section");
      group.className = "icon-option-group";
      const title = document.createElement("div");
      title.className = "icon-option-group-title";
      title.textContent = groupConfig.label;
      const grid = document.createElement("div");
      grid.className = "icon-option-grid";
      for (const icon of groupConfig.icons) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "icon-option";
        button.dataset.icon = icon;
        button.textContent = icon;
        button.title = `${groupConfig.label}: ${icon}`;
        if (hiddenNode.value === icon) {
          button.classList.add("active");
        }
        grid.appendChild(button);
      }
      group.append(title, grid);
      popoverNode.appendChild(group);
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
    toggleIconPopover,
    setupCategoryIconPickers,
  };
})();
