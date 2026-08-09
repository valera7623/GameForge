/**
 * Glossary UI helpers for localization page.
 * Shape: { [term]: { [lang]: translation } }
 */

const STORAGE_PREFIX = "gf_loc_glossary_";

/**
 * @param {string|null|undefined} projectId
 * @returns {string}
 */
export function glossaryStorageKey(projectId) {
  return STORAGE_PREFIX + (projectId || "default");
}

/**
 * @param {string|null|undefined} projectId
 * @returns {Record<string, Record<string, string>>}
 */
export function loadGlossary(projectId) {
  try {
    const raw = localStorage.getItem(glossaryStorageKey(projectId));
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed;
  } catch {
    return {};
  }
}

/**
 * @param {string|null|undefined} projectId
 * @param {Record<string, Record<string, string>>} glossary
 */
export function saveGlossary(projectId, glossary) {
  const key = glossaryStorageKey(projectId);
  if (!glossary || !Object.keys(glossary).length) {
    localStorage.removeItem(key);
    return;
  }
  localStorage.setItem(key, JSON.stringify(glossary));
}

/**
 * @param {string} targetsRaw comma-separated langs
 * @returns {string[]}
 */
export function parseTargetLangs(targetsRaw) {
  return String(targetsRaw || "")
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

/**
 * Read glossary table DOM → object. Skips empty terms.
 * @param {HTMLElement} tbody
 * @param {string[]} langs
 * @returns {Record<string, Record<string, string>>|null}
 */
export function collectGlossaryFromDom(tbody, langs) {
  if (!tbody) return null;
  const out = {};
  tbody.querySelectorAll("tr[data-glossary-row]").forEach((row) => {
    const termInput = row.querySelector('[data-g="term"]');
    const term = (termInput?.value || "").trim();
    if (!term) return;
    const langsMap = {};
    langs.forEach((lang) => {
      const inp = row.querySelector(`[data-g-lang="${lang}"]`);
      const val = (inp?.value || "").trim();
      if (val) langsMap[lang] = val;
    });
    if (Object.keys(langsMap).length) out[term] = langsMap;
  });
  return Object.keys(out).length ? out : null;
}

/**
 * Render editable glossary rows.
 * @param {HTMLElement} tbody
 * @param {HTMLElement} theadRow
 * @param {string[]} langs
 * @param {Record<string, Record<string, string>>} glossary
 * @param {(row: HTMLElement) => void} onRemove
 * @param {{ removeLabel?: string, termPlaceholder?: string, termHeader?: string }} [opts]
 */
export function renderGlossaryTable(tbody, theadRow, langs, glossary, onRemove, opts = {}) {
  theadRow.innerHTML = "";
  const thTerm = document.createElement("th");
  thTerm.textContent = opts.termHeader || "Term";
  theadRow.appendChild(thTerm);
  langs.forEach((lang) => {
    const th = document.createElement("th");
    th.textContent = lang;
    theadRow.appendChild(th);
  });
  const thAct = document.createElement("th");
  thAct.textContent = "";
  theadRow.appendChild(thAct);

  tbody.innerHTML = "";
  const entries = Object.entries(glossary || {});
  if (!entries.length) {
    tbody.appendChild(makeGlossaryRow(langs, "", {}, onRemove, opts));
    return;
  }
  entries.forEach(([term, map]) => {
    tbody.appendChild(makeGlossaryRow(langs, term, map || {}, onRemove, opts));
  });
}

/**
 * @param {string[]} langs
 * @param {string} term
 * @param {Record<string, string>} map
 * @param {(row: HTMLElement) => void} onRemove
 * @param {{ removeLabel?: string, termPlaceholder?: string }} [opts]
 * @returns {HTMLTableRowElement}
 */
export function makeGlossaryRow(langs, term, map, onRemove, opts = {}) {
  const tr = document.createElement("tr");
  tr.dataset.glossaryRow = "1";

  const tdTerm = document.createElement("td");
  const termInp = document.createElement("input");
  termInp.type = "text";
  termInp.dataset.g = "term";
  termInp.value = term || "";
  termInp.placeholder = opts.termPlaceholder || "HeroName";
  termInp.autocomplete = "off";
  tdTerm.appendChild(termInp);
  tr.appendChild(tdTerm);

  langs.forEach((lang) => {
    const td = document.createElement("td");
    const inp = document.createElement("input");
    inp.type = "text";
    inp.dataset.gLang = lang;
    inp.value = map[lang] || "";
    inp.placeholder = lang;
    inp.autocomplete = "off";
    td.appendChild(inp);
    tr.appendChild(td);
  });

  const tdAct = document.createElement("td");
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-ghost";
  btn.textContent = "×";
  btn.setAttribute("aria-label", opts.removeLabel || "Remove");
  btn.addEventListener("click", () => onRemove(tr));
  tdAct.appendChild(btn);
  tr.appendChild(tdAct);

  return tr;
}
