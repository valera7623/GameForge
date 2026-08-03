import { getLang } from "./i18n.js";

/** Base URL for the MkDocs documentation site. */
export function getDocsBaseUrl() {
  const configured = (import.meta.env.VITE_DOCS_URL || "").trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  if (import.meta.env.DEV) {
    return "http://localhost:8001";
  }
  return "https://docs.gameforge.website";
}

/** Documentation URL for the active UI language. */
export function getDocsUrl(lang = getLang()) {
  const base = getDocsBaseUrl();
  return lang === "ru" ? `${base}/ru/` : `${base}/`;
}

/** Update all documentation anchors on the page for the current language. */
export function bindDocsLinks(root = document) {
  const url = getDocsUrl();
  root.querySelectorAll("[data-docs-link]").forEach((el) => {
    el.setAttribute("href", url);
  });
}
