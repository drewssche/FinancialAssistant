(() => {
  const { el } = window.App;
  const actions = getActions();
  const categoryActions = getCategoryActions();
  const pickerUtils = getPickerUtils();
  const pickerCoordinator = getPickerUiCoordinator();
  let bound = false;

  function bindPickerFeatureHandlers() {
    if (bound) {
      return;
    }
    bound = true;
    document.addEventListener("focusin", pickerCoordinator.scrollFocusedModalFieldIntoView);
    pickerCoordinator.bindDatePickerTriggers();

    for (const id of ["opAmount", "opDate", "opNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
        if (id === "opAmount" && actions.renderReceiptSummary) {
          node.addEventListener("input", actions.renderReceiptSummary);
          node.addEventListener("change", actions.renderReceiptSummary);
        }
      }
    }
    pickerCoordinator.bindDateField("opDate", actions.updateCreatePreview);
    for (const id of ["debtCounterparty", "debtPrincipal", "debtStartDate", "debtDueDate", "debtNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
      }
    }
    for (const id of ["currencyAsset", "currencyQuote", "currencyTradeDateModal", "currencyQuantity", "currencyUnitPrice", "currencyFee", "currencyNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
      }
    }
    pickerCoordinator.bindDateField("debtStartDate", actions.updateCreatePreview);
    pickerCoordinator.bindDateField("debtDueDate", actions.updateCreatePreview);
    pickerCoordinator.bindDateField("currencyTradeDateModal", actions.updateCreatePreview);
    pickerCoordinator.bindSearchPicker({
      input: el.debtCounterparty,
      onFocus: actions.handleDebtCounterpartySearchFocus,
      onInput: actions.handleDebtCounterpartySearchInput,
      onKeydown: actions.handleDebtCounterpartySearchKeydown,
      picker: el.debtCounterpartyAll,
      onPickerClick: actions.handleDebtCounterpartyPickerClick,
    });
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
        if (id === "editAmount" && actions.renderReceiptSummary) {
          node.addEventListener("input", () => actions.renderReceiptSummary("edit"));
          node.addEventListener("change", () => actions.renderReceiptSummary("edit"));
        }
      }
    }
    pickerCoordinator.bindDateField("editDate", actions.updateEditPreview);
    pickerCoordinator.bindDateField("bulkOpDate");
    pickerCoordinator.bindDateField("customDateFrom");
    pickerCoordinator.bindDateField("customDateTo");
    pickerCoordinator.bindDateField("repaymentDate");
    pickerCoordinator.bindSearchPicker({
      input: el.editCategorySearch,
      onFocus: actions.handleEditCategorySearchFocus,
      onInput: actions.handleEditCategorySearchInput,
      onKeydown: actions.handleEditCategorySearchKeydown,
      picker: el.editCategoryAll,
      onPickerClick: actions.handleEditCategoryPickerClick,
    });

    pickerCoordinator.bindSearchPicker({
      input: el.opCategorySearch,
      onFocus: actions.handleCreateCategorySearchFocus,
      onInput: actions.handleCreateCategorySearchInput,
      onKeydown: actions.handleCreateCategorySearchKeydown,
      picker: el.opCategoryAll,
      onPickerClick: actions.handleCreateCategoryPickerClick,
    });

    if (el.pullReceiptTotalBtn && actions.handlePullReceiptTotal) {
      el.pullReceiptTotalBtn.addEventListener("click", () => {
        actions.handlePullReceiptTotal("create");
      });
    }
    pickerCoordinator.bindReceiptList(el.receiptItemsList, {
      onInput: actions.handleReceiptItemsListInput,
      onFocusIn: actions.handleReceiptItemsListFocusIn,
      onKeydown: actions.handleReceiptItemsListKeydown,
      onClick: actions.handleReceiptItemsListClick,
    });
    if (el.editPullReceiptTotalBtn && actions.handlePullReceiptTotal) {
      el.editPullReceiptTotalBtn.addEventListener("click", (event) => {
        actions.handlePullReceiptTotal(event);
      });
    }
    pickerCoordinator.bindReceiptList(el.editReceiptItemsList, {
      onInput: actions.handleReceiptItemsListInput,
      onFocusIn: actions.handleReceiptItemsListFocusIn,
      onKeydown: actions.handleReceiptItemsListKeydown,
      onClick: actions.handleReceiptItemsListClick,
    });

    if (el.categoryGroupSearch) {
      el.categoryGroupSearch.addEventListener("focus", () => {
        if (categoryActions.handleCreateGroupSearchFocus) {
          categoryActions.handleCreateGroupSearchFocus();
        }
      });
      el.categoryGroupSearch.addEventListener("click", () => {
        if (categoryActions.handleCreateGroupSearchFocus) {
          categoryActions.handleCreateGroupSearchFocus();
        }
      });
      el.categoryGroupSearch.addEventListener("input", () => {
        if (categoryActions.handleCreateGroupSearchInput) {
          categoryActions.handleCreateGroupSearchInput();
        }
      });
      el.categoryGroupSearch.addEventListener("blur", () => {
        if (categoryActions.handleCreateGroupSearchBlur) {
          categoryActions.handleCreateGroupSearchBlur();
        }
      });
      el.categoryGroupSearch.addEventListener("keydown", (event) => {
        if (categoryActions.handleCreateGroupSearchKeydown) {
          categoryActions.handleCreateGroupSearchKeydown(event);
        }
      });
    }
    if (el.categoryGroupAll) {
      el.categoryGroupAll.addEventListener("click", (event) => {
        if (categoryActions.handleCreateGroupPickerClick) {
          categoryActions.handleCreateGroupPickerClick(event);
        }
      });
    }
    if (el.editCategoryGroupSearch) {
      el.editCategoryGroupSearch.addEventListener("focus", () => {
        if (categoryActions.handleEditGroupSearchFocus) {
          categoryActions.handleEditGroupSearchFocus();
        }
      });
      el.editCategoryGroupSearch.addEventListener("click", () => {
        if (categoryActions.handleEditGroupSearchFocus) {
          categoryActions.handleEditGroupSearchFocus();
        }
      });
      el.editCategoryGroupSearch.addEventListener("input", () => {
        if (categoryActions.handleEditGroupSearchInput) {
          categoryActions.handleEditGroupSearchInput();
        }
      });
      el.editCategoryGroupSearch.addEventListener("blur", () => {
        if (categoryActions.handleEditGroupSearchBlur) {
          categoryActions.handleEditGroupSearchBlur();
        }
      });
      el.editCategoryGroupSearch.addEventListener("keydown", (event) => {
        if (categoryActions.handleEditGroupSearchKeydown) {
          categoryActions.handleEditGroupSearchKeydown(event);
        }
      });
    }
    if (el.editCategoryGroupAll) {
      el.editCategoryGroupAll.addEventListener("click", (event) => {
        if (categoryActions.handleEditGroupPickerClick) {
          categoryActions.handleEditGroupPickerClick(event);
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

    if (el.itemTemplateSourceSearch && actions.updateItemTemplatePreview) {
      for (const eventName of ["input", "change"]) {
        el.itemTemplateSourceSearch.addEventListener(eventName, actions.updateItemTemplatePreview);
      }
    }
    if (el.itemTemplateName && actions.updateItemTemplatePreview) {
      for (const eventName of ["input", "change"]) {
        el.itemTemplateName.addEventListener(eventName, actions.updateItemTemplatePreview);
      }
    }
    if (el.itemTemplatePrice && actions.updateItemTemplatePreview) {
      for (const eventName of ["input", "change"]) {
        el.itemTemplatePrice.addEventListener(eventName, actions.updateItemTemplatePreview);
      }
    }
    if (el.itemTemplatePriceDate && actions.updateItemTemplatePreview) {
      for (const eventName of ["input", "change"]) {
        el.itemTemplatePriceDate.addEventListener(eventName, actions.updateItemTemplatePreview);
      }
    }

    if (el.itemTemplateSourceSearch) {
      el.itemTemplateSourceSearch.addEventListener("focus", () => {
        if (actions.handleItemTemplateSourceSearchFocus) {
          actions.handleItemTemplateSourceSearchFocus();
        }
      });
      el.itemTemplateSourceSearch.addEventListener("click", () => {
        if (actions.handleItemTemplateSourceSearchFocus) {
          actions.handleItemTemplateSourceSearchFocus();
        }
      });
      el.itemTemplateSourceSearch.addEventListener("input", () => {
        if (actions.handleItemTemplateSourceSearchInput) {
          actions.handleItemTemplateSourceSearchInput();
        }
      });
      el.itemTemplateSourceSearch.addEventListener("keydown", (event) => {
        if (actions.handleItemTemplateSourceSearchKeydown) {
          actions.handleItemTemplateSourceSearchKeydown(event);
        }
      });
      el.itemTemplateSourceSearch.addEventListener("focusout", (event) => {
        if (actions.handleItemTemplateSourceSearchFocusOut) {
          actions.handleItemTemplateSourceSearchFocusOut(event);
        }
      });
    }
    if (el.itemTemplateSourceAll) {
      el.itemTemplateSourceAll.addEventListener("click", (event) => {
        if (actions.handleItemTemplateSourcePickerClick) {
          actions.handleItemTemplateSourcePickerClick(event);
        }
      });
    }
    if (el.sourceGroupName && actions.updateSourceGroupPreview) {
      for (const eventName of ["input", "change"]) {
        el.sourceGroupName.addEventListener(eventName, actions.updateSourceGroupPreview);
      }
    }

    document.addEventListener("pointerdown", (event) => {
      if (pickerUtils?.closeOpenPopoversOnOutside) {
        pickerUtils.closeOpenPopoversOnOutside(event);
      }
      if (categoryActions.handleCreateGroupOutsidePointer) {
        categoryActions.handleCreateGroupOutsidePointer(event);
      }
    }, true);
  }

  const api = {
    bindPickerFeatureHandlers,
  };

  window.App.initFeaturePickers = api;
  window.App.registerFeatureInitModule?.("pickers", api);
})();

function getActions() {
  return window.App.actions || {};
}

function getCategoryActions() {
  return window.App.getRuntimeModule?.("category-actions") || {};
}

function getCore() {
  return window.App.core;
}

function getPickerUtils() {
  return window.App.getRuntimeModule?.("picker-utils") || window.App.pickerUtils;
}

function getPickerUiCoordinatorModule() {
  return window.App.getRuntimeModule?.("picker-ui-coordinator");
}

function getPickerUiCoordinator() {
  return (
    getPickerUiCoordinatorModule() || {
      scrollFocusedModalFieldIntoView(event) {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
          return;
        }
        if (!window.matchMedia("(max-width: 640px)").matches) {
          return;
        }
        if (!target.matches("input, textarea, select")) {
          return;
        }
        const modalCard = target.closest(".modal-card");
        const modal = target.closest(".modal");
        if (!modalCard || !modal || modal.classList.contains("hidden")) {
          return;
        }
        const scrollTarget = target.closest(
          ".receipt-item-row, .money-input-wrap, .create-category-field, .debt-due-field, .receipt-summary, .preview-panel, .bulk-import-preview, .field",
        ) || target;
        window.requestAnimationFrame(() => {
          window.setTimeout(() => {
            scrollTarget.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
          }, 120);
        });
      },
      bindDateField(id, onChange = null) {
        const node = document.getElementById(id);
        if (!node) {
          return;
        }
        const normalize = () => {
          getCore().syncDateFieldValue(node, node.value);
          if (typeof onChange === "function") {
            onChange();
          }
        };
        if (node.type === "date") {
          node.addEventListener("input", normalize);
        }
        node.addEventListener("blur", normalize);
        node.addEventListener("change", normalize);
      },
      bindDatePickerTriggers() {
        document.addEventListener("click", (event) => {
          const trigger = event.target.closest("[data-date-picker-trigger]");
          if (!trigger) {
            return;
          }
          event.preventDefault();
          const targetId = String(trigger.dataset.datePickerTrigger || "").trim();
          if (!targetId) {
            return;
          }
          const input = document.getElementById(targetId);
          if (!(input instanceof HTMLInputElement) || input.disabled || input.readOnly) {
            return;
          }
          if (typeof input.showPicker === "function") {
            try {
              input.showPicker();
              return;
            } catch {}
          }
          input.focus({ preventScroll: true });
          input.click();
        });
      },
      bindSearchPicker({ input, onFocus, onInput, onKeydown, picker, onPickerClick, onBlur = null }) {
        if (input) {
          if (typeof onFocus === "function") {
            input.addEventListener("focus", onFocus);
            input.addEventListener("click", onFocus);
          }
          if (typeof onInput === "function") {
            input.addEventListener("input", onInput);
          }
          if (typeof onKeydown === "function") {
            input.addEventListener("keydown", onKeydown);
          }
          if (typeof onBlur === "function") {
            input.addEventListener("blur", onBlur);
          }
        }
        if (picker && typeof onPickerClick === "function") {
          picker.addEventListener("click", onPickerClick);
        }
      },
      bindReceiptList(container, handlers) {
        if (!container) {
          return;
        }
        if (typeof handlers.onInput === "function") {
          container.addEventListener("input", handlers.onInput);
        }
        if (typeof handlers.onFocusIn === "function") {
          container.addEventListener("focusin", handlers.onFocusIn);
        }
        if (typeof handlers.onKeydown === "function") {
          container.addEventListener("keydown", handlers.onKeydown);
        }
        if (typeof handlers.onClick === "function") {
          container.addEventListener("click", handlers.onClick);
        }
      },
    }
  );
}
