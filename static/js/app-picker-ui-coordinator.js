(() => {
  window.App = window.App || {};

  function getCore() {
    return window.App.core;
  }

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
  }

  function bindDatePickerTriggers() {
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
  }

  function bindSearchPicker({ input, onFocus, onInput, onKeydown, picker, onPickerClick, onBlur = null }) {
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
  }

  function bindReceiptList(container, handlers) {
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
  }

  const api = {
    scrollFocusedModalFieldIntoView,
    bindDateField,
    bindDatePickerTriggers,
    bindSearchPicker,
    bindReceiptList,
  };

  window.App.registerRuntimeModule?.("picker-ui-coordinator", api);
})();
