(() => {
  // Integer cents and thousandths avoid binary floating point rounding of receipts.
  const scaled = (value, digits) => {
    const number = Number(String(value ?? 0).replace(",", "."));
    if (!Number.isFinite(number) || Math.abs(number) >= 1e12) return 0n;
    return BigInt(number.toFixed(digits).replace(".", ""));
  };
  const roundedDivide = (n, d) => (n + d / 2n) / d;
  function paidUnitPrice(total, quantity) {
    const thousandths = scaled(quantity, 3);
    return thousandths > 0n ? Number(roundedDivide(scaled(total, 2) * 1000n, thousandths)) / 100 : null;
  }
  function calculate(item) {
    const quantity = scaled(item.quantity, 3);
    if (!item.discount_mode) {
      return { total: Number(roundedDivide(quantity * scaled(item.unit_price, 2), 1000n)) / 100, subtotal: null };
    }
    const known = Number(item.regular_unit_price) > 0;
    const subtotal = known ? roundedDivide(quantity * scaled(item.regular_unit_price, 2), 1000n) : null;
    let total;
    if (item.discount_mode === "final") total = scaled(item.discount_value, 2);
    else if (subtotal === null) return { total: 0, subtotal: null, error: "Укажите цену до скидки" };
    else if (item.discount_mode === "amount") total = subtotal - scaled(item.discount_value, 2);
    else total = subtotal - roundedDivide(subtotal * scaled(item.discount_value, 4), 1000000n);
    const value = Number(item.discount_value);
    const error = quantity <= 0n ? "Укажите количество" :
      !Number.isFinite(value) || value < 0 || (item.discount_mode === "percent" && value >= 100) ? "Проверьте скидку" :
      total <= 0n ? "Итог должен быть больше нуля" :
      subtotal !== null && total > subtotal ? "Итог превышает сумму до скидки" : "";
    return { total: Number(total) / 100, subtotal: subtotal === null ? null : Number(subtotal) / 100, error };
  }
  function savedAmounts(row) {
    const total = row.line_total != null ? Number(row.line_total) : calculate(row).total;
    if (!row.is_discounted) return {total, subtotal: null};
    if (row.line_subtotal != null) return {total, subtotal: Number(row.line_subtotal)};
    // Older receipts only store the regular unit price. Round the whole line as at checkout.
    const subtotal = Number(row.regular_unit_price) > 0
      ? calculate({quantity: row.quantity, unit_price: row.regular_unit_price}).total : null;
    return {total, subtotal};
  }
  function compare(item, previous) {
    const current = calculate(item);
    const qty = scaled(item.quantity, 3), oldQty = scaled(previous.quantity, 3);
    const paid = scaled(current.total, 2), oldPaid = scaled(previous.line_total, 2);
    if (current.error || qty <= 0n || oldQty <= 0n || paid <= 0n || oldPaid < 0n) return null;
    const numerator = paid * oldQty - oldPaid * qty;
    const denominator = oldPaid * qty;
    const signedRound = (n, d) => n < 0n ? -roundedDivide(-n, d) : roundedDivide(n, d);
    return {
      percent: denominator > 0n ? Number(signedRound(numerator * 10000n, denominator)) / 100 : null,
      direction: numerator > 0n ? 1 : numerator < 0n ? -1 : 0,
      difference: Number(paid - roundedDivide(oldPaid * qty, oldQty)) / 100,
      currentPrice: Number(paid) * 10 / Number(qty),
    };
  }
  function payload(item) {
    const price = calculate(item);
    return {
      discount_mode: item.discount_mode || null,
      discount_value: item.discount_mode ? String(item.discount_value ?? 0) : null,
      ...(item.discount_mode ? { unit_price: (price.total / Number(item.quantity || 1)).toFixed(6) } : {}),
    };
  }
  window.App = window.App || {};
  window.App.receiptPricing = { calculate, savedAmounts, paidUnitPrice, payload, compare };
})();
