# Table Pattern Contract

Переиспользуемый модуль: `static/table_pattern.js`

## API
`createTableController(config)` возвращает:
- `bind()` - подписывает UI события (`search/min/sort`)
- `render()` - рендерит строки таблицы

## Config
Обязательные поля:
- `rowsEl`: tbody element
- `searchEl`: input element
- `minEl`: input number element
- `sortEl`: select element
- `emptyText`: string
- `getRows`: function -> `[{ name: string, amount: number }]`
- `getTotal`: function -> number
- `formatAmount`: function(number) -> string

## Features
- search по `name`
- filter по min amount
- sort (`amount_desc`, `amount_asc`, `name_asc`, `name_desc`)
- highlight совпадений в колонке `name`
- auto empty-state

## Usage Example
```js
const controller = createTableController({
  rowsEl,
  searchEl,
  minEl,
  sortEl,
  emptyText: "Нет данных",
  getRows: () => data,
  getTotal: () => total,
  formatAmount: (v) => Number(v).toFixed(2),
});

controller.bind();
controller.render();
```
