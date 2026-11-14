(() => {
  const parse = text => [...new Set(String(text || "").split(",")
    .map(value => value.trim().replace(/^#+/, "").trim().replace(/\s+/g, " ").normalize().toLowerCase()).filter(Boolean))];
  const all = entry => [...new Set([...(entry?.tags || []), ...(entry?.receipt_items || []).flatMap(line => line.tags || [])])];
  const text = tags => (tags || []).map(tag => "#" + tag).join(" ");
  const chips = tags => (tags || []).map(tag => {
    const value = window.App.core.escapeHtml(tag);
    return `<button type="button" data-purchase-tag="${value}" class="chip-btn">#${value}</button>`;
  }).join(" ");

  async function open(tag) {
    const core = window.App.core;
    const dialog = document.createElement("dialog");
    dialog.className = "purchase-tags-dialog";
    dialog.setAttribute("aria-label", "Расходы и планы по тегу");
    dialog.innerHTML = '<div class="modal-head"><strong></strong><button type="button" class="btn btn-secondary" aria-label="Закрыть">×</button></div><div role="status">Загрузка…</div>';
    dialog.querySelector("strong").textContent = "#" + tag;
    dialog.querySelector("button").onclick = () => dialog.close();
    dialog.addEventListener("close", () => dialog.remove(), {once:true});
    document.body.append(dialog);
    dialog.showModal();
    const body = dialog.querySelector('[role="status"]');
    try {
      const result = await core.requestJson("/api/v1/operations/purpose-tags/summary?tag=" + encodeURIComponent(tag), {headers:core.authHeaders()});
      if (!dialog.open) return;
      body.replaceChildren();
      for (const [title, group] of [["Потрачено", result.paid], ["Запланировано", result.planned]]) {
        const section = document.createElement("section");
        const heading = document.createElement("h3");
        const totals = Object.entries(group.totals).map(([currency, amount]) => core.formatMoney(amount, {currency}));
        heading.textContent = title + (totals.length ? " · " + totals.join(" + ") : "");
        section.append(heading);
        for (const item of group.entries) {
          const line = document.createElement("p");
          line.textContent = [core.formatDateRu(item.date), item.note || (title === "Потрачено" ? "Операция" : "План") + " №" + item.id, core.formatMoney(item.amount, {currency:item.currency})].join(" · ");
          section.append(line);
        }
        if (!group.count) section.append("Нет записей");
        if (group.count > group.entries.length) section.append(`Показано ${group.entries.length} из ${group.count}`);
        body.append(section);
      }
    } catch (error) {
      body.textContent = error?.message || "Не удалось загрузить расходы и планы";
    }
  }
  document.addEventListener("click", event => {
    const trigger = event.target.closest?.("button[data-purchase-tag]");
    if (trigger) { event.stopPropagation(); open(trigger.dataset.purchaseTag); }
  }, true);
  window.App.purchaseTags = {parse, all, text, chips};
})();
