(() => {
  // Contract shared with app/core/search.py; never use for stored identities.
  const enKeys = "`qwertyuiop[]asdfghjkl;'zxcvbnm,.";
  const ruKeys = "ёйцукенгшщзхъфывапролджэячсмитьбю";
  const normalize = (value) => String(value ?? "").toLowerCase().replaceAll("ё", "е").trim().replace(/\s+/gu, " ");
  const translate = (value, from, to) => Array.from(value, (char) => from.includes(char) ? to[from.indexOf(char)] : char).join("");

  function variants(query) {
    const raw = String(query ?? "").toLowerCase();
    const result = [normalize(raw)];
    if (/[a-z]/u.test(raw)) result.push(normalize(translate(raw, enKeys + '~{}:"<>', ruKeys + "ёхъжэбю")));
    if (/[а-яё]/u.test(raw)) result.push(normalize(translate(raw, ruKeys, enKeys)));
    return [...new Set(result)];
  }

  function rank(value, query) {
    const text = normalize(value);
    const options = variants(query);
    const index = options.findIndex((option) => text.includes(option));
    return index < 0 ? options.length : index;
  }

  function matches(value, query) {
    return rank(value, query) < variants(query).length;
  }

  function compare(query, left, right) {
    const score = (values) => Math.min(...[].concat(values).map((value) => rank(value, query)));
    return score(left) - score(right);
  }

  function prioritize(items, query, values = (item) => item.name) {
    return [...items].sort((a, b) => compare(query, values(a), values(b)));
  }

  function highlightRanges(value, query) {
    if (!normalize(query)) return [];
    const escape = (char) => char.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pattern = variants(query).map((variant) => Array.from(variant, (char) => (
      char === "е" ? "[её]" : char === " " ? "\\s+" : escape(char)
    )).join("")).join("|");
    return Array.from(String(value ?? "").matchAll(new RegExp(pattern, "giu")), (match) => [match.index, match.index + match[0].length]);
  }

  window.App.search = { normalize, variants, rank, matches, compare, prioritize, highlightRanges };
})();
