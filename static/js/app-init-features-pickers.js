(() => {
  const { el, actions } = window.App;
  let bound = false;

  function bindPickerFeatureHandlers() {
    if (bound) {
      return;
    }
    bound = true;

    for (const id of ["opAmount", "opDate", "opNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
      }
    }
    for (const id of ["debtCounterparty", "debtPrincipal", "debtStartDate", "debtDueDate", "debtNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
      }
    }
    if (actions.updateDebtDueHint) {
      const dueNodes = [document.getElementById("debtStartDate"), document.getElementById("debtDueDate")];
      for (const node of dueNodes) {
        if (!node) {
          continue;
        }
        node.addEventListener("input", actions.updateDebtDueHint);
        node.addEventListener("change", actions.updateDebtDueHint);
      }
    }
    for (const id of ["editAmount", "editDate", "editNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateEditPreview);
        node.addEventListener("change", actions.updateEditPreview);
      }
    }
    el.editCategory.addEventListener("change", () => {
      if (actions.updateEditPreview) {
        actions.updateEditPreview();
      }
    });

    el.opCategorySearch.addEventListener("focus", () => {
      if (actions.handleCreateCategorySearchFocus) {
        actions.handleCreateCategorySearchFocus();
      }
    });
    el.opCategorySearch.addEventListener("click", () => {
      if (actions.handleCreateCategorySearchFocus) {
        actions.handleCreateCategorySearchFocus();
      }
    });
    el.opCategorySearch.addEventListener("input", () => {
      if (actions.handleCreateCategorySearchInput) {
        actions.handleCreateCategorySearchInput();
      }
    });
    el.opCategorySearch.addEventListener("keydown", (event) => {
      if (actions.handleCreateCategorySearchKeydown) {
        actions.handleCreateCategorySearchKeydown(event);
      }
    });
    if (el.opCategoryAll) {
      el.opCategoryAll.addEventListener("click", (event) => {
        if (actions.handleCreateCategoryPickerClick) {
          actions.handleCreateCategoryPickerClick(event);
        }
      });
    }

    if (el.categoryGroupSearch) {
      el.categoryGroupSearch.addEventListener("focus", () => {
        if (actions.handleCreateGroupSearchFocus) {
          actions.handleCreateGroupSearchFocus();
        }
      });
      el.categoryGroupSearch.addEventListener("click", () => {
        if (actions.handleCreateGroupSearchFocus) {
          actions.handleCreateGroupSearchFocus();
        }
      });
      el.categoryGroupSearch.addEventListener("input", () => {
        if (actions.handleCreateGroupSearchInput) {
          actions.handleCreateGroupSearchInput();
        }
      });
      el.categoryGroupSearch.addEventListener("blur", () => {
        if (actions.handleCreateGroupSearchBlur) {
          actions.handleCreateGroupSearchBlur();
        }
      });
      el.categoryGroupSearch.addEventListener("keydown", (event) => {
        if (actions.handleCreateGroupSearchKeydown) {
          actions.handleCreateGroupSearchKeydown(event);
        }
      });
    }
    if (el.categoryGroupAll) {
      el.categoryGroupAll.addEventListener("click", (event) => {
        if (actions.handleCreateGroupPickerClick) {
          actions.handleCreateGroupPickerClick(event);
        }
      });
    }
    if (el.editCategoryGroupSearch) {
      el.editCategoryGroupSearch.addEventListener("focus", () => {
        if (actions.handleEditGroupSearchFocus) {
          actions.handleEditGroupSearchFocus();
        }
      });
      el.editCategoryGroupSearch.addEventListener("click", () => {
        if (actions.handleEditGroupSearchFocus) {
          actions.handleEditGroupSearchFocus();
        }
      });
      el.editCategoryGroupSearch.addEventListener("input", () => {
        if (actions.handleEditGroupSearchInput) {
          actions.handleEditGroupSearchInput();
        }
      });
      el.editCategoryGroupSearch.addEventListener("blur", () => {
        if (actions.handleEditGroupSearchBlur) {
          actions.handleEditGroupSearchBlur();
        }
      });
      el.editCategoryGroupSearch.addEventListener("keydown", (event) => {
        if (actions.handleEditGroupSearchKeydown) {
          actions.handleEditGroupSearchKeydown(event);
        }
      });
    }
    if (el.editCategoryGroupAll) {
      el.editCategoryGroupAll.addEventListener("click", (event) => {
        if (actions.handleEditGroupPickerClick) {
          actions.handleEditGroupPickerClick(event);
        }
      });
    }

    if (el.createPreviewBody) {
      el.createPreviewBody.addEventListener("click", (event) => {
        if (actions.handleCreatePreviewClick) {
          actions.handleCreatePreviewClick(event);
        }
      });
    }

    document.addEventListener("pointerdown", (event) => {
      if (actions.handleCreateCategoryOutsidePointer) {
        actions.handleCreateCategoryOutsidePointer(event);
      }
      if (actions.handleCreateGroupOutsidePointer) {
        actions.handleCreateGroupOutsidePointer(event);
      }
    });
  }

  window.App.initFeaturePickers = {
    bindPickerFeatureHandlers,
  };
})();
