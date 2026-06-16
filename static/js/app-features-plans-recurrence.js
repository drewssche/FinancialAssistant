(() => {
  function createPlansRecurrenceFeature(deps) {
    const { el, core } = deps;

    function isWorkdaysOnlyEnabled() {
      return String(el.planRecurrenceWorkdaysOnly?.value || "off") === "on";
    }

    function isMonthEndModeEnabled() {
      return String(el.planRecurrenceMonthEnd?.value || "off") === "on";
    }

    function getMonthEndIso(isoDate) {
      const normalized = core.parseDateInputValue(isoDate || "") || core.getTodayIso();
      const [year, month] = normalized.split("-").map((value) => Number(value || 0));
      if (!year || !month) {
        return core.getTodayIso();
      }
      const lastDay = new Date(year, month, 0).getDate();
      return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
    }

    function syncMonthEndScheduleDateLock() {
      const opDateInput = document.getElementById("opDate");
      const opDateWrap = document.getElementById("opDateField");
      const opDateTrigger = opDateWrap?.querySelector(".date-input-trigger");
      const shouldLock = (el.planScheduleMode?.value || "oneoff") === "recurring"
        && (el.planRecurrenceFrequency?.value || "monthly") === "monthly"
        && isMonthEndModeEnabled();
      if (!opDateInput) {
        return;
      }
      if (shouldLock) {
        core.syncDateFieldValue(opDateInput, getMonthEndIso(opDateInput.value || core.getTodayIso()));
      }
      opDateInput.disabled = shouldLock;
      if (opDateTrigger) {
        opDateTrigger.disabled = shouldLock;
        opDateTrigger.setAttribute("aria-disabled", shouldLock ? "true" : "false");
      }
      opDateWrap?.classList.toggle("is-disabled", shouldLock);
    }

    function setMonthEndMode(enabled) {
      const next = enabled ? "on" : "off";
      if (el.planRecurrenceMonthEnd) {
        el.planRecurrenceMonthEnd.value = next;
      }
      if (el.planRecurrenceMonthEndSwitch) {
        core.syncSegmentedActive(el.planRecurrenceMonthEndSwitch, "plan-month-end", next);
      }
      syncMonthEndScheduleDateLock();
    }

    function setWorkdaysOnlyMode(enabled) {
      const next = enabled ? "on" : "off";
      if (el.planRecurrenceWorkdaysOnly) {
        el.planRecurrenceWorkdaysOnly.value = next;
      }
      if (el.planRecurrenceWorkdaysSwitch) {
        core.syncSegmentedActive(el.planRecurrenceWorkdaysSwitch, "plan-workdays-only", next);
      }
    }

    function getPlanAnchorWeekday() {
      const scheduledDate = core.parseDateInputValue(document.getElementById("opDate")?.value || "") || core.getTodayIso();
      const anchor = new Date(`${scheduledDate}T00:00:00`);
      const jsWeekday = anchor.getDay();
      return (jsWeekday + 6) % 7;
    }

    function getSelectedPlanWeekdays() {
      if (!el.planRecurrenceWeekdays) {
        return [];
      }
      return Array.from(el.planRecurrenceWeekdays.querySelectorAll("button[data-plan-weekday].active"))
        .map((button) => Number(button.dataset.planWeekday || 0))
        .filter((value) => Number.isInteger(value) && value >= 0 && value <= 6)
        .sort((a, b) => a - b);
    }

    function setSelectedPlanWeekdays(values) {
      if (!el.planRecurrenceWeekdays) {
        return;
      }
      const selected = new Set(Array.isArray(values) ? values.map((value) => Number(value)) : []);
      Array.from(el.planRecurrenceWeekdays.querySelectorAll("button[data-plan-weekday]")).forEach((button) => {
        const weekday = Number(button.dataset.planWeekday || 0);
        button.classList.toggle("active", selected.has(weekday));
      });
    }

    function syncPlanRecurrenceUi() {
      const enabled = (el.planScheduleMode?.value || "oneoff") === "recurring";
      el.planRecurrenceFields?.classList.toggle("hidden", !enabled);
      const frequency = el.planRecurrenceFrequency?.value || "monthly";
      const daily = enabled && frequency === "daily";
      const weekly = enabled && frequency === "weekly";
      const monthly = enabled && frequency === "monthly";
      el.planRecurrenceWorkdaysWrap?.classList.toggle("hidden", !daily);
      el.planRecurrenceWeeklyBlock?.classList.toggle("hidden", !weekly);
      el.planRecurrenceMonthEndWrap?.classList.toggle("hidden", !monthly);
      if (!daily && el.planRecurrenceWorkdaysOnly) {
        setWorkdaysOnlyMode(false);
      }
      if (weekly && !getSelectedPlanWeekdays().length) {
        setSelectedPlanWeekdays([getPlanAnchorWeekday()]);
      }
      if (!weekly) {
        setSelectedPlanWeekdays([]);
      }
      if (!monthly && el.planRecurrenceMonthEnd) {
        setMonthEndMode(false);
      }
      syncMonthEndScheduleDateLock();
    }

    function togglePlanWeekday(weekday) {
      if (!el.planRecurrenceWeekdays || Number.isNaN(weekday)) {
        return;
      }
      const button = el.planRecurrenceWeekdays.querySelector(`button[data-plan-weekday="${weekday}"]`);
      if (!button) {
        return;
      }
      const selected = new Set(getSelectedPlanWeekdays());
      if (selected.has(weekday) && selected.size > 1) {
        selected.delete(weekday);
      } else {
        selected.add(weekday);
      }
      setSelectedPlanWeekdays(Array.from(selected));
    }

    return {
      isWorkdaysOnlyEnabled,
      isMonthEndModeEnabled,
      setMonthEndMode,
      setWorkdaysOnlyMode,
      syncPlanRecurrenceUi,
      getSelectedPlanWeekdays,
      setSelectedPlanWeekdays,
      togglePlanWeekday,
    };
  }

  window.App.registerRuntimeModule?.("plans-recurrence", createPlansRecurrenceFeature);
})();
