(() => {
  const {core} = window.App;
  const node = (id) => document.getElementById(id), esc = (s) => core.escapeHtml(String(s ?? ""));
  let product = null, data = null, generation = 0, controller = null, bound = false;
  const dirtyForms = new Set();
  const fields = ["sale_unit", "package_quantity", "package_unit"];
  const url = () => `/api/v1/operations/catalog-products/${product.id}`;
  function variantForm() {
    const v = data?.variants?.find((v) => String(v.id) === node("catalogVariantSelect").value);
    node("catalogVariantName").value = v?.name || "";
    for (const key of fields) node(`catalogVariant_${key}`).value = v?.[key] ?? "";
    node("catalogVariantCodes").value = (v?.codes || []).join("\n");
    node("catalogVariantArchived").checked = Boolean(v?.is_archived);
  }
  function offerForm() {
    const m = data?.offers?.find((m) => String(m.template_id) === node("catalogIdentityOffer").value);
    node("catalogIdentityVariant").value = m?.variant_id || "";
    node("catalogIdentityCode").value = m?.retailer_code || "";
    node("catalogIdentityName").value = m?.external_name || "";
    node("catalogIdentityUrl").value = m?.product_url || "";
  }
  function options() {
    const selected = node("catalogVariantSelect").value, mapped = node("catalogIdentityVariant").value;
    const variants = (data?.variants || []).map((v) => `<option value="${Number(v.id)}">${esc(v.name)}${v.is_archived ? " · архив" : ""}</option>`).join("");
    node("catalogVariantSelect").innerHTML = '<option value="">Новая фасовка</option>'+variants;
    node("catalogIdentityVariant").innerHTML = '<option value="">Без связи с фасовкой</option>'+variants;
    node("catalogVariantSelect").value = selected;
    node("catalogIdentityVariant").value = mapped;
  }
  async function load() {
    controller?.abort(); controller = new AbortController();
    const token = ++generation;
    node("catalogIdentityStatus").textContent = "Загрузка…";
    node("catalogIdentityForms").classList.add("hidden");
    try {
      const payload = await core.requestJson(`${url()}/identity`, {headers: core.authHeaders(), signal: controller.signal});
      if (token !== generation) return;
      data = payload; dirtyForms.clear();
      node("catalogIdentityStatus").textContent = "Сохраняется отдельно от основной карточки. Прошлые чеки не изменяются.";
      node("catalogIdentityOffer").innerHTML = (product.offers || []).map((o) => `<option value="${Number(o.template_id)}">${esc(o.source_name || "Без источника")} · ${esc(o.name)}</option>`).join("");
      node("catalogOfferIdentityForm").classList.toggle("hidden", !(product.offers || []).length);
      options(); variantForm(); offerForm();
      node("catalogIdentityForms").classList.remove("hidden");
    } catch (error) {
      if (token === generation && error.name !== "AbortError") node("catalogIdentityStatus").textContent = `Не удалось загрузить: ${error.message}. Вернитесь на вкладку для повтора.`;
    }
  }
  async function save(form, variant) {
    if (!product || !data) return;
    const token = generation, id = node("catalogVariantSelect").value;
    const buttons = [...node("catalogIdentityForms").querySelectorAll('button[type="submit"]')]; buttons.forEach((b) => b.disabled = true);
    let payload, path, method;
    if (variant) {
      payload = {name: node("catalogVariantName").value, codes: node("catalogVariantCodes").value.split(/[\s,;]+/).filter(Boolean), is_archived: node("catalogVariantArchived").checked};
      for (const key of fields) payload[key] = node(`catalogVariant_${key}`).value || null;
      path = `${url()}/variants${id ? `/${id}` : ""}`; method = id ? "PUT" : "POST";
    } else {
      payload = {variant_id: Number(node("catalogIdentityVariant").value) || null, retailer_code: node("catalogIdentityCode").value || null, external_name: node("catalogIdentityName").value || null, product_url: node("catalogIdentityUrl").value || null};
      path = `${url()}/offers/${Number(node("catalogIdentityOffer").value)}/identity`; method = "PUT";
    }
    try {
      const previousIds = new Set((data.variants || []).map((v) => v.id));
      const response = await core.requestJson(path, {method, headers: {...core.authHeaders(), "Content-Type": "application/json"}, body: JSON.stringify(payload)});
      window.App.getRuntimeModule("catalog-products").invalidate();
      if (token !== generation) return;
      data = response; dirtyForms.delete(form.id); options();
      if (variant) {
        node("catalogVariantSelect").value = id || data.variants.find((v) => !previousIds.has(v.id))?.id || "";
        variantForm();
      }
      node("catalogIdentityStatus").textContent = "Сохранено. Прошлые чеки не изменились.";
    } catch (error) {
      if (token === generation) node("catalogIdentityStatus").textContent = `Не удалось сохранить: ${error.message}`;
    } finally { if (token === generation) buttons.forEach((b) => b.disabled = false); }
  }
  function bind() {
    if (bound) return; bound = true;
    node("catalogIdentityForms").addEventListener("input", (event) => {dirtyForms.add(event.target.closest("form")?.id);});
    node("catalogVariantSelect").addEventListener("change", variantForm);
    node("catalogIdentityOffer").addEventListener("change", offerForm);
    node("catalogVariantForm").addEventListener("submit", (e) => {e.preventDefault(); save(e.currentTarget, true);});
    node("catalogOfferIdentityForm").addEventListener("submit", (e) => {e.preventDefault(); save(e.currentTarget, false);});
  }
  let active = false;
  function activate(value) { active = value; if (active && product && !data && !dirtyForms.size) load(); }
  function close() {active = false;generation++; controller?.abort(); product = null; data = null; dirtyForms.clear();}
  window.App.registerRuntimeModule("catalog-identity", {
    open(value) {close(); bind(); product = value; node("catalogIdentityDetails").classList.toggle("hidden", !value); node("catalogVariantSelect").value = ""; node("catalogIdentityForms").querySelectorAll('button[type="submit"]').forEach((b) => b.disabled = false);},
    refresh(value) {product = value; if (dirtyForms.size) return; data = null; if (active) load();},
    activate, close, cleanup: close,
  });
})();
