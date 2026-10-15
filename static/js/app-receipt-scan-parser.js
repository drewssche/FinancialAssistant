(() => {
  // Conservative extraction: never repair digits, infer packaging or merge repeated rows.
  const money = value => /^\d{1,7}[.,]\d{2}$/.test(String(value).trim()) ? Math.round(Number(String(value).replace(',', '.')) * 100) : null;
  const subtotal = (price, quantity) => Number((BigInt(price) * BigInt(Math.round(quantity * 1000)) + 500n) / 1000n);
  const amountAtEnd = line => money(line.match(/(\d{1,7}[.,]\d{2})\s*$/)?.[1] || '');
  function validDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const d = new Date(`${value}T12:00:00Z`);
    return !isNaN(d) && d.toISOString().slice(0, 10) === value;
  }
  function parse(text) {
    const lines = String(text).slice(0, 80000).split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const unsupported = /возврат|сторно/i.test(text);
    const rows = [], dates = new Set(), totals = new Set(), warnings = [];
    let names = [], ended = false, pendingDiscount = false, pendingDiscountType = 'promo', shop = '';
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Camera watermark and promotion dates are not purchase timestamps.
      if (!/redmi|note\s*\d|дата (начала|окончания)|действия|акци/i.test(line)) {
        const stamp = line.match(/\b(\d{2})\.(\d{2})\.(20\d{2})\s+(\d{2}:\d{2}:\d{2})/);
        if (stamp) { const date = `${stamp[3]}-${stamp[2]}-${stamp[1]}`; if (validDate(date)) dates.add(date); }
      }
      if (!shop && /(?:ООО|ОАО|ЧТУП|магазин|аптека|общество с)/i.test(line) && !ended) shop = line;
      if (/итого\s*к\s*оплате/i.test(line)) {
        const value = amountAtEnd(line) ?? (/^\d+[.,]\d{2}$/.test(lines[i + 1] || '') ? money(lines[i + 1]) : null);
        if (value !== null) totals.add(value);
      }
      if (/^(итого|банк|кассир|оплата|фишки|номер карты)/i.test(line)) { ended = true; names = []; }
      if (ended) continue;
      if (pendingDiscount && !/^[-−]?\s*\d+[.,]\d{2}$/.test(line) && !/скидк|оплата бонус/i.test(line)) pendingDiscount = false;
      if (/скидк|оплата бонус/i.test(line) || pendingDiscount) {
        if (/скидк|оплата бонус/i.test(line)) pendingDiscountType = /бонус|балл/i.test(line) ? 'loyalty_points' : 'promo';
        const discount = amountAtEnd(line.replace(/[-−]\s*(\d)/g, '$1'));
        if (rows.length && discount !== null) {
          const row = rows[rows.length - 1];
          row.discount += discount; row.discount_type = pendingDiscountType;
          row.total = row.printed_total - row.discount; row.source += '\n' + line;
          pendingDiscount = false;
        } else pendingDiscount = /скидк/i.test(line);
        if (/скидк|оплата бонус/i.test(line) || pendingDiscount || /^[-−]?\s*\d+[.,]\d{2}$/.test(line)) continue;
      }
      const match = line.match(/(\d{1,7}[.,]\d{2})\s*[xхХX×*]\s*(\d{1,7}(?:[.,]\d{1,3})?)\s+(\d{1,7}[.,]\d{2})\s*$/);
      if (match) {
        if (rows.length >= 151) continue;
        if (/[-−]\s*$/.test(line.slice(0, match.index))) {warnings.push('Отрицательные позиции требуют ручного ввода');continue;}
        const prefix = line.slice(0, match.index).replace(/^\d{8,14}\s*/, '').trim();
        const name = [...names, prefix].filter(Boolean).join(' ').trim();
        const price = money(match[1]), quantity = Number(match[2].replace(',', '.')), total = money(match[3]);
        const calculated = subtotal(price, quantity);
        rows.push({name, price, quantity, printed_total: total, total, discount: 0, discount_type: null,
          source: [...names, line].join('\n'), issue: calculated !== total ? 'Цена × количество не совпадает с суммой строки' : ''});
        names = []; pendingDiscount = false;
      } else if (/^[\d\s.,*xх−-]+$/.test(line)) continue;
      else if (/упн|скко|платеж|документ|^№\s*док|кол.?во|^цена|^г\.\s*минск|^чек:|^касса/i.test(line)) names = [];
      else if (/[а-яa-z]/i.test(line)) names = [...names, line.replace(/^\d{8,14}\s*/, '')].slice(-3);
    }
    if (dates.size !== 1) warnings.push('Проверьте дату покупки по чеку');
    if (totals.size !== 1) warnings.push('Проверьте итог к оплате');
    if (!rows.length) warnings.push('Строки не распознаны — исправьте текст или добавьте вручную');
    if (rows.some(r => r.issue)) warnings.push('Есть строки с несовпадением цены и количества');
    return {unsupported: unsupported || warnings.includes('Отрицательные позиции требуют ручного ввода'), date: dates.size === 1 ? [...dates][0] : '', shop, total: totals.size === 1 ? [...totals][0] : null, rows, warnings};
  }
  function validate(draft) {
    const errors = [];
    if (draft.unsupported) errors.push('Возврат или отрицательная позиция: используйте ручной ввод операции');
    if (!validDate(draft.date)) errors.push('Укажите дату покупки');
    if (!draft.shop.trim() || draft.shop.length > 160) errors.push('Укажите магазин');
    if (!Number.isInteger(draft.total) || draft.total <= 0) errors.push('Укажите итог чека');
    if (!draft.rows.length || draft.rows.length > 150) errors.push('В чеке должно быть от 1 до 150 позиций');
    let sum = 0;
    draft.rows.forEach((r, i) => {
      if (!r.name.trim() || r.name.length > 160 || !Number.isFinite(r.quantity) || r.quantity <= 0 || r.quantity > 100000 || Math.abs(r.quantity * 1000 - Math.round(r.quantity * 1000)) > 1e-6 || !Number.isInteger(r.price) || r.price <= 0 || !Number.isInteger(r.discount) || r.discount < 0 || !Number.isInteger(r.total) || r.total <= 0) errors.push(`Проверьте поля позиции ${i + 1}`);
      else if (subtotal(r.price, r.quantity) - r.discount !== r.total) errors.push(`Проверьте цену, количество и скидку позиции ${i + 1}`);
      sum += r.total || 0;
    });
    if (sum !== draft.total) errors.push(`Сумма позиций ${(sum / 100).toFixed(2)} не совпадает с итогом чека`);
    return errors;
  }
  window.App.receiptScanParser = {parse, validate, money};
})();
