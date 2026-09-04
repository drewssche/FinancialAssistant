(() => {
  const registry = Object.freeze({
    operation: Object.freeze({
      row: Object.freeze(["receipt", "activity", "edit", "delete"]),
      modal: Object.freeze(["receipt", "activity"]),
    }),
    item_template: Object.freeze({
      row: Object.freeze(["activity", "usage", "history", "edit", "delete"]),
      modal: Object.freeze(["activity", "usage", "history"]),
    }),
    item_brand: Object.freeze({
      row: Object.freeze(["edit", "delete"]),
      modal: Object.freeze(["edit"]),
    }),
    category: Object.freeze({
      row: Object.freeze(["activity", "usage", "edit", "delete"]),
      modal: Object.freeze(["activity", "usage"]),
    }),
    category_group: Object.freeze({
      row: Object.freeze(["create_child", "activity", "edit", "delete"]),
      modal: Object.freeze(["create_child", "activity"]),
    }),
    item_source: Object.freeze({
      row: Object.freeze(["create_child", "edit", "delete"]),
      modal: Object.freeze(["create_child"]),
    }),
  });

  function keys(entityType, context = "row") {
    const definition = registry[String(entityType || "")];
    const values = definition?.[String(context || "row")];
    return Array.isArray(values) ? [...values] : [];
  }

  function has(entityType, context, actionKey) {
    return keys(entityType, context).includes(String(actionKey || ""));
  }

  window.App.registerRuntimeModule?.("context-actions", { registry, keys, has });
})();
