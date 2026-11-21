(() => {
  const parse = text => [...new Set(String(text || "").split(",")
    .map(value => value.trim().replace(/^#+/, "").trim().replace(/\s+/g, " ").normalize().toLowerCase()).filter(Boolean))];
  const all = entry => [...new Set([...(entry?.tags || []), ...(entry?.receipt_items || []).flatMap(line => line.tags || [])])];
  const text = tags => (tags || []).map(tag => "#" + tag).join(" ");
  const chips = tags => (tags || []).map(tag => {
    const value = window.App.core.escapeHtml(tag);
    return `<button type="button" data-purchase-tag="${value}" class="chip-btn">#${value}</button>`;
  }).join(" ");

  const { formatMoney, formatDateRu } = window.App.core;

  function element(tag, className, label) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (label != null) node.textContent = label;
    return node;
  }

  function signedMoney(amount, currency, kind) {
    const sign = Number(amount) === 0 ? "" : kind === "expense" ? "−" : "+";
    return sign + formatMoney(amount, { currency });
  }

  function balanceCard(currency, amounts, converted, showCurrencyCode) {
    const net = Number(amounts.net);
    const kind = net < 0 ? "expense" : net > 0 ? "income" : "neutral";
    const titles = { expense: "Итог · расход", income: "Итог · доход", neutral: "Нулевой баланс" };
    const card = element("section", "tag-balance");
    const result = element("div", "tag-result");
    const title = showCurrencyCode ? titles[kind] + " · " + currency : titles[kind];
    result.append(element("h3", "tag-caption", title),
      element("strong", "tag-net amount-" + kind, signedMoney(Math.abs(net), currency, kind)));
    if (converted) result.append(element("small", "tag-caption", "По курсам на даты операций"));
    const breakdown = element("dl", "tag-breakdown");
    for (const [key, label] of [["income", "Доходы"], ["expense", "Расходы"]]) {
      const pair = element("div");
      pair.append(element("dt", "tag-caption", label), element("dd", "", formatMoney(amounts[key], { currency })));
      breakdown.append(pair);
    }
    card.append(result, breakdown);
    return card;
  }

  function activitySection(income, expense, planned) {
    const count = income.count + expense.count;
    const section = element("section", "tag-activity");
    const heading = element("h3", "tag-section-title", planned ? "Запланировано" : "Операции");
    section.append(heading);
    if (!count) {
      section.append(element("p", "tag-caption", "Пока нет операций по этому тегу."));
      return section;
    }
    heading.append(element("span", "tag-count", count));
    if (planned) {
      const forecast = element("div", "tag-forecast");
      for (const [group, label] of [[income, "К получению"], [expense, "К оплате"]]) {
        const amounts = Object.entries(group.totals).map(([currency, amount]) => formatMoney(amount, { currency }));
        if (amounts.length) forecast.append(element("span", "", label + " · " + amounts.join(" / ")));
      }
      section.append(forecast);
    }
    const entries = [
      ...income.entries.map(item => ({ ...item, kind: "income" })),
      ...expense.entries.map(item => ({ ...item, kind: "expense" })),
    ].sort((a, b) => (planned ? 1 : -1) * a.date.localeCompare(b.date) || a.id - b.id).slice(0, 30);
    const list = element("ul", "tag-entries");
    for (const item of entries) {
      const row = element("li", "tag-entry");
      const info = element("div", "tag-entry-info");
      const label = item.description || item.note || (planned ? "План №" : "Операция №") + item.id;
      const date = element("time", "tag-caption", formatDateRu(item.date));
      date.dateTime = item.date;
      info.append(element("span", "", label), date);
      row.append(info, element("strong", "tag-entry-amount amount-" + item.kind, signedMoney(item.amount, item.currency, item.kind)));
      list.append(row);
    }
    section.append(list);
    if (entries.length < count) section.append(element("p", "tag-caption", `Показано ${entries.length} из ${count}`));
    return section;
  }

  async function open(tag) {
    const core = window.App.core;
    const dialog = element("dialog", "purchase-tags-dialog");
    dialog.setAttribute("aria-label", "Сводка по тегу #" + tag);
    dialog.innerHTML = `<header class="tag-dialog-head"><h2 tabindex="-1"></h2><button type="button" class="btn btn-secondary btn-icon" aria-label="Закрыть сводку" title="Закрыть">${window.App.icons.svg("close")}</button></header><div class="tag-dialog-body"><p role="status" class="tag-caption">Загрузка…</p></div>`;
    const title = dialog.querySelector("h2");
    title.append(element("span", "tag-hash", "#"), document.createTextNode(tag));
    dialog.querySelector("button").onclick = () => dialog.close();
    const controller = new AbortController();
    dialog.addEventListener("close", () => { controller.abort(); dialog.remove(); }, { once: true });
    document.body.append(dialog);
    dialog.showModal();
    title.focus({ preventScroll: true });
    const body = dialog.querySelector(".tag-dialog-body");
    try {
      const result = await core.requestJson("/api/v1/operations/purpose-tags/summary?tag=" + encodeURIComponent(tag), {
        headers: core.authHeaders(), signal: controller.signal,
      });
      if (!dialog.open) return;
      const balances = Object.entries(result.balances);
      const cards = balances.map(([currency, amounts]) => balanceCard(currency, amounts, result.converted, balances.length > 1));
      const sections = [...cards, activitySection(result.received, result.paid, false)];
      if (result.planned.count || result.planned_income.count) {
        sections.push(activitySection(result.planned_income, result.planned, true));
      }
      body.replaceChildren(...sections);
    } catch (error) {
      if (dialog.open) body.querySelector('[role="status"]').textContent = error?.message || "Не удалось загрузить сводку по тегу.";
    }
  }
  document.addEventListener("click", event => {
    const trigger = event.target.closest?.("button[data-purchase-tag]");
    if (trigger) { event.stopPropagation(); open(trigger.dataset.purchaseTag); }
  }, true);
  window.App.purchaseTags = {parse, all, text, chips};
})();
