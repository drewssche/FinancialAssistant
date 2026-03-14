(() => {
  const { el, actions, core } = window.App;
  let bound = false;

  function isCompactModalViewport() {
    return window.matchMedia("(max-width: 640px)").matches;
  }

  function scrollFocusedModalFieldIntoView(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (!isCompactModalViewport()) {
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
  }

  function bindDateField(id, onChange = null) {
    const node = document.getElementById(id);
    if (!node) {
      return;
    }
    const normalize = () => {
      core.syncDateFieldValue(node, node.value);
      if (typeof onChange === "function") {
        onChange();
      }
    };
    if (node.type === "date") {
      node.addEventListener("input", normalize);
    }
    node.addEventListener("blur", normalize);
    node.addEventListener("change", normalize);
  }

  function bindPickerFeatureHandlers() {
    if (bound) {
      return;
    }
    bound = true;
    document.addEventListener("focusin", scrollFocusedModalFieldIntoView);
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
    bindDateField("opDate", actions.updateCreatePreview);
    for (const id of ["debtCounterparty", "debtPrincipal", "debtStartDate", "debtDueDate", "debtNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
      }
    }
    bindDateField("debtStartDate", actions.updateCreatePreview);
    bindDateField("debtDueDate", actions.updateCreatePreview);
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
    bindDateField("editDate", actions.updateEditPreview);
    bindDateField("bulkOpDate");
    bindDateField("customDateFrom");
    bindDateField("customDateTo");
    bindDateField("repaymentDate");
    if (el.editCategorySearch) {
      el.editCategorySearch.addEventListener("focus", () => {
        if (actions.handleEditCategorySearchFocus) {
          actions.handleEditCategorySearchFocus();
        }
      });
      el.editCategorySearch.addEventListener("click", () => {
        if (actions.handleEditCategorySearchFocus) {
          actions.handleEditCategorySearchFocus();
        }
      });
      el.editCategorySearch.addEventListener("input", () => {
        if (actions.handleEditCategorySearchInput) {
          actions.handleEditCategorySearchInput();
        }
      });
      el.editCategorySearch.addEventListener("keydown", (event) => {
        if (actions.handleEditCategorySearchKeydown) {
          actions.handleEditCategorySearchKeydown(event);
        }
      });
    }
    if (el.editCategoryAll) {
      el.editCategoryAll.addEventListener("click", (event) => {
        if (actions.handleEditCategoryPickerClick) {
          actions.handleEditCategoryPickerClick(event);
        }
      });
    }

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

    if (el.pullReceiptTotalBtn && actions.handlePullReceiptTotal) {
      el.pullReceiptTotalBtn.addEventListener("click", () => {
        actions.handlePullReceiptTotal("create");
      });
    }
    if (el.receiptItemsList) {
      el.receiptItemsList.addEventListener("input", (event) => {
        if (actions.handleReceiptItemsListInput) {
          actions.handleReceiptItemsListInput(event);
        }
      });
      el.receiptItemsList.addEventListener("focusin", (event) => {
        if (actions.handleReceiptItemsListFocusIn) {
          actions.handleReceiptItemsListFocusIn(event);
        }
      });
      el.receiptItemsList.addEventListener("keydown", (event) => {
        if (actions.handleReceiptItemsListKeydown) {
          actions.handleReceiptItemsListKeydown(event);
        }
      });
      el.receiptItemsList.addEventListener("click", (event) => {
        if (actions.handleReceiptItemsListClick) {
          actions.handleReceiptItemsListClick(event);
        }
      });
    }
    if (el.editPullReceiptTotalBtn && actions.handlePullReceiptTotal) {
      el.editPullReceiptTotalBtn.addEventListener("click", (event) => {
        actions.handlePullReceiptTotal(event);
      });
    }
    if (el.editReceiptItemsList) {
      el.editReceiptItemsList.addEventListener("input", (event) => {
        if (actions.handleReceiptItemsListInput) {
          actions.handleReceiptItemsListInput(event);
        }
      });
      el.editReceiptItemsList.addEventListener("focusin", (event) => {
        if (actions.handleReceiptItemsListFocusIn) {
          actions.handleReceiptItemsListFocusIn(event);
        }
      });
      el.editReceiptItemsList.addEventListener("keydown", (event) => {
        if (actions.handleReceiptItemsListKeydown) {
          actions.handleReceiptItemsListKeydown(event);
        }
      });
      el.editReceiptItemsList.addEventListener("click", (event) => {
        if (actions.handleReceiptItemsListClick) {
          actions.handleReceiptItemsListClick(event);
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
      if (actions.handleCreateCategoryOutsidePointer) {
        actions.handleCreateCategoryOutsidePointer(event);
      }
      if (actions.handleEditCategoryOutsidePointer) {
        actions.handleEditCategoryOutsidePointer(event);
      }
      if (actions.handleReceiptOutsidePointer) {
        actions.handleReceiptOutsidePointer(event);
      }
      if (actions.handleCreateGroupOutsidePointer) {
        actions.handleCreateGroupOutsidePointer(event);
      }
      if (actions.handleItemTemplateSourceOutsidePointer) {
        actions.handleItemTemplateSourceOutsidePointer(event);
      }
    }, true);
  }

  window.App.initFeaturePickers = {
    bindPickerFeatureHandlers,
  };
})();
