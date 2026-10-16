(() => {
  const {core} = window.App;
  const node = (id) => document.getElementById(id), esc = (s) => core.escapeHtml(String(s ?? ""));
  let product = null, data = null, generation = 0, controller = null, bound = false;
  const dirtyForms = new Set();
  const variantDrafts = new Map();
  const fields = ["sale_unit", "package_quantity", "package_unit"];
  const url = () => `/api/v1/operations/catalog-products/${product.id}`;
  function variantForm() {
    const v = variantDrafts.get(node("catalogVariantSelect").value) || data?.variants?.find((v) => String(v.id) === node("catalogVariantSelect").value);
    node("catalogVariantName").value = v?.name || "";
    for (const key of fields) node(`catalogVariant_${key}`).value = v?.[key] ?? "";
    node("catalogVariantCodes").value = (v?.codes || []).join("\n");
    node("catalogVariantArchived").checked = Boolean(v?.is_archived);
    window.App.measurements.mount(node("catalogVariant_sale_unit").closest('.form-grid'), fields.map(key => node(`catalogVariant_${key}`)));
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
    node('catalogVariantList').innerHTML = (data?.variants || []).map(v => `<button type="button" class="package-list-row" data-edit-variant="${Number(v.id)}"><span><strong>${esc(v.name)}</strong><small>${esc(window.App.measurements.summary(v))}${v.codes?.length?' · '+esc(v.codes.join(', ')):''}${v.is_archived?' · архив':''}</small></span>${window.App.icons.svg('edit')}</button>`).join('') || '<p class="muted-small">Дополнительных размеров нет. Обычный размер укажите во вкладке «Товар».</p>';
  }
  const quick = () => window.App.getRuntimeModule("catalog-product-codes");
  async function load() {
    quick().loading();
    controller?.abort(); controller = new AbortController();
    const token = ++generation;
    node("catalogIdentityStatus").textContent = "Загрузка…";
    node("catalogIdentityForms").classList.add("hidden");
    try {
      const payload = await core.requestJson(`${url()}/identity`, {headers: core.authHeaders(), signal: controller.signal});
      if (token !== generation) return;
      data = payload; quick().accept(data); dirtyForms.clear(); variantDrafts.clear();
      node("catalogIdentityStatus").textContent = "";
      node("catalogIdentityOffer").innerHTML = (product.offers || []).map((o) => `<option value="${Number(o.template_id)}">${esc(o.source_name || "Без источника")} · ${esc(o.name)}</option>`).join("");
      node("catalogOfferIdentityForm").classList.toggle("hidden", !(product.offers || []).length);
      options(); variantForm(); offerForm();
      node("catalogIdentityForms").classList.remove("hidden");
    } catch (error) {
      if (token === generation && error.name !== "AbortError") {quick().failed(); node("catalogIdentityStatus").textContent = `Не удалось загрузить: ${error.message}. Вернитесь на вкладку для повтора.`;}
    } finally {if(token===generation)controller=null;}
  }
  async function save(form, variant) {
    if (!product || !data) return;
    const token = generation, id = node("catalogVariantSelect").value;
    const buttons = [...node("catalogIdentityForms").querySelectorAll('button[type="submit"]')]; buttons.forEach((b) => b.disabled = true);
    let payload, path, method;
    if (variant) {
      payload = {name: node("catalogVariantName").value.trim() || window.App.measurements.summary(Object.fromEntries(fields.map(key => [key,node(`catalogVariant_${key}`).value]))), codes: node("catalogVariantCodes").value.split(/[\s,;]+/).filter(Boolean), is_archived: node("catalogVariantArchived").checked};
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
      data = response; quick().accept(data); dirtyForms.delete(form.id);
      if (variant) variantDrafts.delete(id);
      if (variantDrafts.size) dirtyForms.add("catalogVariantForm");
      options();
      if (variant) {
        node("catalogVariantSelect").value = id || data.variants.find((v) => !previousIds.has(v.id))?.id || "";
        variantForm();
      }
      node("catalogIdentityStatus").textContent = "Сохранено";
      if (variant) {showVariant(false); node("catalogVariantList").querySelector(`[data-edit-variant="${node("catalogVariantSelect").value}"]`)?.focus();}
    } catch (error) {
      if (token === generation) node("catalogIdentityStatus").textContent = `Не удалось сохранить: ${error.message}`;
    } finally { if (token === generation) buttons.forEach((b) => b.disabled = false); }
  }
  function showVariant(show) {
    node('catalogVariantForm').hidden = !show;
    node('catalogVariantListView').hidden = show;
  }
  function bind() {
    if (bound) return; bound = true;
    document.querySelector('.package-tasks').addEventListener('click', e => {
      const button = e.target.closest('[data-package-task]'); if (!button) return;
      button.closest('[data-product-panel]').dataset.packageView = button.dataset.packageTask;
      document.querySelectorAll('[data-package-task]').forEach(b => {const active=b===button; b.classList.toggle('active',active); b.setAttribute('aria-pressed',String(active));});
    });
    node('catalogVariantAdd').addEventListener('click', () => {node('catalogVariantSelect').value=''; variantForm(); showVariant(true);});
    node('catalogVariantBack').addEventListener('click', () => showVariant(false));
    node('catalogVariantList').addEventListener('click', e => {const b=e.target.closest('[data-edit-variant]'); if(!b)return; node('catalogVariantSelect').value=b.dataset.editVariant; variantForm(); showVariant(true);});
    node("catalogIdentityForms").addEventListener("input", (event) => {
      const formId=event.target.closest('form')?.id; dirtyForms.add(formId);
      if (formId==='catalogVariantForm') variantDrafts.set(node('catalogVariantSelect').value, {
        name:node('catalogVariantName').value, codes:node('catalogVariantCodes').value.split(/\n/), is_archived:node('catalogVariantArchived').checked,
        ...Object.fromEntries(fields.map(key => [key,node(`catalogVariant_${key}`).value])),
      });
    });
    node("catalogVariantSelect").addEventListener("change", variantForm);
    node("catalogIdentityOffer").addEventListener("change", offerForm);
    node("catalogVariantForm").addEventListener("submit", (e) => {e.preventDefault(); save(e.currentTarget, true);});
    node("catalogOfferIdentityForm").addEventListener("submit", (e) => {e.preventDefault(); save(e.currentTarget, false);});
  }
  let active = false;
  function activate(value) { active = value; if (active && product && !data && !controller && !dirtyForms.size) load(); }
  function close() {quick().close();active = false;generation++; controller?.abort(); controller=null; product = null; data = null; dirtyForms.clear(); variantDrafts.clear();}
  window.App.registerRuntimeModule("catalog-identity", {
    open(value) {close(); bind(); showVariant(false); document.querySelector('[data-package-task="sizes"]').click(); product = value; quick().open(value); if(value)load(); node("catalogIdentityDetails").classList.toggle("hidden", !value); node("catalogVariantSelect").value = ""; node("catalogIdentityForms").querySelectorAll('button[type="submit"]').forEach((b) => b.disabled = false);},
    refresh(value) {product = value; quick().refresh(value); if (dirtyForms.size) return; data = null; load();},
    reload: load, activate, close, cleanup: close,
  });
})();
