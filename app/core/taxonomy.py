from __future__ import annotations

DEFAULT_GROUPED_CATEGORIES: dict[str, list[dict[str, object]]] = {
    "income": [
        {
            "name": "Основной доход",
            "color": "#3ddc97",
            "icon": "💼",
            "categories": ["ЗП", "Дополнительный"],
        },
        {
            "name": "Прочие поступления",
            "color": "#6ec8ff",
            "icon": "✨",
            "categories": ["Возврат", "Скидка/кешбек", "Подарок+", "Находка"],
        },
    ],
    "expense": [
        {
            "name": "Базовые платежи",
            "color": "#5aa6ff",
            "icon": "🏠",
            "categories": ["Коммуналка", "Телефон", "Интернет", "Налоги/Комиссии", "Штрафы"],
        },
        {
            "name": "Еда",
            "color": "#4fb9a7",
            "icon": "🍽️",
            "categories": ["Продукты и быт", "Обед на работе", "Кофе", "Снеки и сладости"],
        },
        {
            "name": "Здоровье и уход",
            "color": "#6ca5ff",
            "icon": "💊",
            "categories": ["Здоровье", "Гигиена/Бытовая химия", "Барбер", "Сигареты"],
        },
        {
            "name": "Покупки и сервис",
            "color": "#7b98ff",
            "icon": "🛍️",
            "categories": ["Онлайн-покупки", "Одежда", "Техника и инструменты", "Ремонт/сервисный центр"],
        },
        {
            "name": "Досуг",
            "color": "#8f8cff",
            "icon": "🎉",
            "categories": ["Игры/Софт/Курсы", "Отдых/Путешествие", "Заведения", "Тренировки", "Проезд"],
        },
        {
            "name": "Подарки и форс-мажоры",
            "color": "#c188ff",
            "icon": "🎁",
            "categories": ["Дни рождения/Подарки", "Подарок-", "Потеря/Украдено", "Подписки"],
        },
    ],
}

DEFAULT_CATEGORY_MAP: dict[str, list[str]] = {
    kind: [name for grp in groups for name in grp["categories"]]  # type: ignore[index]
    for kind, groups in DEFAULT_GROUPED_CATEGORIES.items()
}

DEFAULT_ACCOUNTS = ["Карта", "Наличные"]
