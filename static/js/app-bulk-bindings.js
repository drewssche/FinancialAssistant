(() => {
  let handlersBound = false;

  function bindBulkHandlers() {
    if (handlersBound) {
      return;
    }
    handlersBound = true;

    window.App.bulkBindingsOperations.bindOperationBulkHandlers();
    window.App.bulkBindingsCategories.bindCategoryBulkHandlers();
    if (window.App.bulkBindingsItemCatalog?.bindItemCatalogBulkHandlers) {
      window.App.bulkBindingsItemCatalog.bindItemCatalogBulkHandlers();
    }
  }

  window.App.bulkBindings = {
    bindBulkHandlers,
  };
})();
