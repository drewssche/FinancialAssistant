(() => {
  const { el } = window.App;
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils") || window.App.pickerUtils;

  // Prefer emoji available in older system fonts too. Newer symbols such as
  // teapot, chair, potted plant, razor, toothbrush and coin can render as tofu
  // squares on otherwise supported browsers.
  const CATEGORY_ICON_GROUPS = [
    {
      label: "Продукты и готовая еда",
      icons: [
        ["🍽️", "Обед / готовая еда"], ["🍔", "Фастфуд"], ["🥐", "Выпечка"], ["🍞", "Хлеб"],
        ["🥖", "Хлеб и багеты"], ["🥩", "Мясо"], ["🍗", "Птица"], ["🐟", "Рыба"],
        ["🍣", "Суши"], ["🍤", "Морепродукты"], ["🍳", "Завтрак"], ["🍲", "Кулинария"],
        ["🍝", "Паста"], ["🍕", "Перекус / пицца"], ["🌭", "Колбаса / сосиски"], ["🥓", "Колбасные и мясные изделия"],
        ["🥪", "Сэндвичи"],
        ["🥗", "Овощи / салаты"], ["🍟", "Снэки"], ["🍿", "Снэки"], ["❄️", "Замороженные продукты"],
        ["🥫", "Консервы"], ["🥛", "Молочные продукты"], ["🧀", "Сыр"], ["🥚", "Яйца"],
      ],
    },
    {
      label: "Фрукты, сладости и напитки",
      icons: [
        ["🍎", "Фрукты"], ["🍌", "Бананы"], ["🍇", "Виноград"], ["🍓", "Ягоды"],
        ["🍉", "Арбуз"], ["🍊", "Цитрусовые"], ["🍑", "Фрукты"], ["🍒", "Ягоды"],
        ["🍰", "Десерты"], ["🍪", "Печенье"], ["🍫", "Шоколад"], ["🍬", "Сладости"],
        ["🍯", "Мёд"], ["🥤", "Газировки / соки"], ["☕", "Кофе"], ["🍵", "Чай"],
        ["🍺", "Пиво"], ["🍷", "Вино"], ["🥃", "Крепкий алкоголь"], ["🔥", "Шашлыки / природа"],
      ],
    },
    {
      label: "Дом, связь и счета",
      icons: [
        ["🏠", "Жильё / коммунальные услуги"], ["🏡", "Дом"], ["🏢", "Аренда / недвижимость"], ["🛋️", "Мебель"],
        ["🛏️", "Дом и спальня"], ["🚪", "Дом и ремонт"], ["🌵", "Растения"], ["🧹", "Уборка"],
        ["🧺", "Стирка"], ["💡", "Электричество"], ["🚿", "Вода"], ["🔥", "Отопление / газ"],
        ["🔌", "Электричество"], ["📱", "Мобильная связь"], ["📞", "Телефон"], ["📺", "Телевидение"],
        ["📶", "Связь"], ["🌐", "Интернет"], ["🔁", "Подписки"], ["🧾", "Счета и квитанции"],
      ],
    },
    {
      label: "Здоровье и уход",
      icons: [
        ["💊", "Аптека / лекарства"], ["🏥", "Медицинские услуги"], ["⚕️", "Здоровье"], ["🦷", "Стоматология"],
        ["👓", "Зрение / очки"], ["🧘", "Здоровье / восстановление"], ["💆", "Массаж"], ["💇", "Парикмахер / барбер"],
        ["✂️", "Барбер / стрижка"], ["💅", "Красота"], ["🧴", "Уход"], ["🧼", "Гигиена"],
        ["🛁", "Уход за собой"], ["🌡️", "Лечение"], ["❤️", "Здоровье"], ["🚑", "Срочная помощь"],
        ["🚬", "Сигареты"], ["🚭", "Без табака"],
      ],
    },
    {
      label: "Покупки и услуги",
      icons: [
        ["🛒", "Продукты / покупки"], ["🏪", "Магазин"], ["🏬", "Торговый центр"], ["🛍️", "Покупки"],
        ["👕", "Одежда"], ["👖", "Одежда"], ["👟", "Обувь"], ["⌚", "Аксессуары"],
        ["📦", "Онлайн-покупки / посылки"], ["💻", "Техника / электроника"], ["📱", "Телефон"], ["🎮", "Игры / софт"],
        ["🔧", "Ремонт / сервис"], ["🔨", "Инструменты"], ["🛠️", "Работы и инструменты"], ["🔑", "Аренда / ключи"],
        ["🚻", "Туалет"], ["✂️", "Услуги"], ["🧵", "Ремонт одежды"], ["📸", "Фотоуслуги"],
      ],
    },
    {
      label: "Транспорт и поездки",
      icons: [
        ["🚕", "Такси"], ["🚇", "Метро"], ["🚌", "Общественный транспорт"], ["🚎", "Троллейбус"],
        ["🚋", "Трамвай"], ["🚗", "Автомобиль"], ["🚙", "Автомобиль"], ["🛵", "Самокат / скутер"],
        ["🚲", "Велосипед"], ["⛽", "Топливо"], ["🅿️", "Парковка"], ["🔑", "Аренда транспорта"],
        ["🧳", "Путешествия"], ["✈️", "Перелёты"], ["🚆", "Поезд"], ["🚢", "Корабль"],
        ["🏨", "Отель"], ["🗺️", "Поездки"], ["🏖️", "Отдых"], ["🏕️", "Походы"],
      ],
    },
    {
      label: "Работа и развитие",
      icons: [
        ["💼", "Работа"], ["💻", "Удалённая работа"], ["🖥️", "Техника / разработка"], ["⌨️", "Работа за компьютером"],
        ["🎓", "Образование"], ["📚", "Книги / курсы"], ["🧠", "Обучение"], ["📝", "Учёба / документы"],
        ["📅", "Планирование"], ["📣", "Реклама / продвижение"], ["👥", "Коллеги / коллектив"], ["🤝", "Партнёрство"],
        ["🏆", "Премия / достижение"], ["⏱️", "Рабочее время"], ["🏭", "Производство"], ["🏢", "Офис"],
      ],
    },
    {
      label: "Досуг, спорт и события",
      icons: [
        ["🎧", "Музыка"], ["🎮", "Игры"], ["🎬", "Кино"], ["🎵", "Развлечения"],
        ["⚽", "Спорт"], ["🏀", "Спорт"], ["🏋️", "Тренировки"], ["🏊", "Бассейн"],
        ["🎨", "Хобби"], ["🎯", "Развлечения"], ["🎳", "Развлечения"], ["🎰", "Ставки / азартные игры"],
        ["🍻", "Бары / встречи"], ["🎁", "Подарки"], ["🎂", "Дни рождения"], ["🎉", "Праздники"],
        ["🙏", "Благотворительность"], ["🐾", "Животные"], ["👶", "Дети"], ["🧸", "Игрушки"],
      ],
    },
    {
      label: "Финансы и доходы",
      icons: [
        ["💰", "Деньги / доход"], ["💵", "Зарплата"], ["💶", "Евро"], ["💷", "Фунты"],
        ["💸", "Расходы / подписки"], ["💎", "Накопления"], ["📈", "Доход / рост"], ["📉", "Расход / снижение"],
        ["🏦", "Банк"], ["💳", "Карта / зарплата"], ["🏧", "Наличные"], ["💱", "Обмен валют"],
        ["↩️", "Возврат / компенсация"], ["↔️", "Перевод"], ["⚖️", "Расхождение / баланс"], ["🧾", "Налоги / комиссии"],
        ["⚠️", "Штрафы"], ["🎰", "Ставки"], ["🎁", "Подарок"], ["💻", "Подработка / фриланс"],
      ],
    },
    {
      label: "Документы и прочее",
      icons: [
        ["📄", "Документы"], ["📋", "Список / учёт"], ["📊", "Статистика"], ["📬", "Почта"],
        ["🔒", "Безопасность"], ["🔎", "Поиск / потеря"], ["❓", "Не определено"], ["❗", "Важно"],
        ["⚠️", "Предупреждение"], ["🚫", "Запрет / списание"], ["🗑️", "Утрата / списание"], ["➕", "Добавление"],
        ["➖", "Вычитание"], ["✅", "Готово"], ["📌", "Важное"], ["💬", "Комментарий"],
      ],
    },
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
      for (const [icon, label] of groupConfig.icons) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "icon-option";
        button.dataset.icon = icon;
        button.textContent = icon;
        button.title = label;
        button.setAttribute("aria-label", label);
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
