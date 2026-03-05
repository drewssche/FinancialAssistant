(() => {
  let handlersBound = false;

  function bindBulkHandlers() {
    if (handlersBound) {
      return;
    }
    handlersBound = true;

    window.App.bulkBindingsOperations.bindOperationBulkHandlers();
    window.App.bulkBindingsCategories.bindCategoryBulkHandlers();
  }

  window.App.bulkBindings = {
    bindBulkHandlers,
  };
})();
