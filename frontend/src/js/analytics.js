/**
 * Analytics — GA4 + Yandex Metrika when env IDs are set at build time.
 *
 * Tracking runs for all visitors. The Metrika corner badge is visible only
 * to GameForge admin and super_admin.
 */

const MEASUREMENT_ID = (import.meta.env.VITE_GA_MEASUREMENT_ID || "").trim();
const METRIKA_ID = String(import.meta.env.VITE_YANDEX_METRIKA_ID || "").trim();

let started = false;
let badgeObserver = null;
let scanTimer = null;

function loadGtag(id) {
  if (typeof window === "undefined" || !id) return;

  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag() {
    window.dataLayer.push(arguments);
  };
  window.gtag("js", new Date());
  window.gtag("config", id, {
    send_page_view: true,
    anonymize_ip: true,
  });

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.appendChild(script);
}

function loadMetrika(id) {
  if (typeof window === "undefined" || !id || !/^\d+$/.test(id)) return;

  (function (m, e, t, r, i, k, a) {
    m[i] =
      m[i] ||
      function () {
        (m[i].a = m[i].a || []).push(arguments);
      };
    m[i].l = 1 * new Date();
    for (var j = 0; j < document.scripts.length; j++) {
      if (document.scripts[j].src === r) return;
    }
    (k = e.createElement(t)), (a = e.getElementsByTagName(t)[0]);
    k.async = 1;
    k.src = r;
    a.parentNode.insertBefore(k, a);
  })(window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");

  window.ym(Number(id), "init", {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: false,
  });

  const noscript = document.createElement("noscript");
  noscript.innerHTML = `<div><img src="https://mc.yandex.ru/watch/${id}" style="position:absolute;left:-9999px" alt="" /></div>`;
  document.body.appendChild(noscript);
}

function canSeeMetrikaBadge() {
  try {
    const u = JSON.parse(localStorage.getItem("gf_user") || "null");
    return Boolean(u && (u.role === "super_admin" || u.role === "admin"));
  } catch {
    return false;
  }
}

function ensureGateCss() {
  let style = document.getElementById("gf-metrika-gate-css");
  if (!style) {
    style = document.createElement("style");
    style.id = "gf-metrika-gate-css";
    document.head.appendChild(style);
  }
  style.textContent = canSeeMetrikaBadge()
    ? ""
    : `
    html.gf-hide-metrika-ui .gf-hide-corner-widget,
    html.gf-hide-metrika-ui a[href*="metrika.yandex"],
    html.gf-hide-metrika-ui a[href*="metrica.yandex"],
    html.gf-hide-metrika-ui a[href*="informer.yandex"],
    html.gf-hide-metrika-ui a[href*="yandex.ru/metrika"],
    html.gf-hide-metrika-ui a[href*="yandex.com/metrika"],
    html.gf-hide-metrika-ui img[src*="informer.yandex"],
    html.gf-hide-metrika-ui img[src*="metrika.yandex"],
    html.gf-hide-metrika-ui img[src*="mc.yandex"],
    html.gf-hide-metrika-ui iframe[src*="metrika.yandex"],
    html.gf-hide-metrika-ui iframe[src*="mc.yandex.ru"],
    html.gf-hide-metrika-ui iframe[src*="mc.yandex.com"],
    html.gf-hide-metrika-ui iframe[src*="yandex.ru"],
    html.gf-hide-metrika-ui iframe[src*="yandex.com"],
    html.gf-hide-metrika-ui .ym-advanced-informer,
    html.gf-hide-metrika-ui [class*="ym-informer"],
    html.gf-hide-metrika-ui [class*="ym-"],
    html.gf-hide-metrika-ui [class*="metrika"],
    html.gf-hide-metrika-ui [id*="ymWidget"],
    html.gf-hide-metrika-ui [id*="yandex_metrika"],
    html.gf-hide-metrika-ui [id*="YaMetrika"],
    html.gf-hide-metrika-ui [id*="YaCounter"],
    html.gf-hide-metrika-ui .gf-metrika-badge {
      display: none !important;
      visibility: hidden !important;
      pointer-events: none !important;
      opacity: 0 !important;
      width: 0 !important;
      height: 0 !important;
      overflow: hidden !important;
    }
  `;
}

function isOurUi(el) {
  if (!el || el.nodeType !== 1) return true;
  if (el.id === "toast-live" || el.closest?.("#toast-live")) return true;
  if (el.classList?.contains("toast") || el.closest?.(".toast")) return true;
  if (el.classList?.contains("theme-toggle") || el.closest?.(".theme-toggle")) return true;
  if (el.classList?.contains("modal-overlay") || el.closest?.(".modal-overlay")) return true;
  if (el.closest?.(".sidebar") || el.closest?.(".app-shell") || el.closest?.(".main-panel")) return true;
  if (el.id === "gf-metrika-gate-css" || el.id === "gf-metrika-badge-css") return true;
  return false;
}

function looksLikeTrackingPixel(el) {
  if (el.tagName !== "IMG") return false;
  const style = el.getAttribute("style") || "";
  return /left:\s*-9999px|position:\s*absolute/i.test(style) || (el.width <= 1 && el.height <= 1);
}

function isMetrikaMarked(el) {
  if (!el || el.nodeType !== 1) return false;
  if (el.id === "gf-metrika-badge" || el.classList?.contains("gf-metrika-badge")) return true;
  if (el.classList?.contains("gf-hide-corner-widget")) return true;

  const href = `${el.getAttribute?.("href") || ""} ${el.href || ""}`;
  const src = `${el.getAttribute?.("src") || ""} ${el.src || ""}`;
  const cls = `${el.className || ""}`;
  const id = `${el.id || ""}`;
  const title = `${el.getAttribute?.("title") || ""} ${el.getAttribute?.("aria-label") || ""}`;
  const html = (el.outerHTML || "").slice(0, 2500);

  if (looksLikeTrackingPixel(el)) return false;

  if (/metrika\.yandex|metrica\.yandex|informer\.yandex|yandex\.(ru|com)\/metrika/i.test(href)) return true;
  if (/informer\.yandex|metrika\.yandex|mc\.yandex/i.test(src)) return true;
  if (/ym-advanced-informer|ym-informer|metrika|YaMetrika|ymWidget/i.test(`${cls} ${id}`)) return true;
  if (/Яндекс\.?\s*Метрик|Yandex\.?\s*Metrica/i.test(title)) return true;
  if (/metrika|metrica|informer\.yandex|mc\.yandex|Яндекс\.?\s*Метрик/i.test(html)) return true;

  try {
    const bg = window.getComputedStyle(el).backgroundImage || "";
    if (/informer\.yandex|metrika\.yandex|mc\.yandex/i.test(bg)) return true;
  } catch {
    /* ignore */
  }

  return false;
}

/** Small fixed/sticky widgets anchored to the bottom-right (Metrika badge etc.). */
function isCornerFloatingWidget(el) {
  if (!el || el.nodeType !== 1 || isOurUi(el)) return false;
  try {
    const cs = window.getComputedStyle(el);
    if (cs.position !== "fixed" && cs.position !== "sticky") return false;
    if (cs.display === "none" || cs.visibility === "hidden") return false;

    const r = el.getBoundingClientRect();
    const w = r.width;
    const h = r.height;
    if (w < 18 || h < 18 || w > 180 || h > 180) return false;

    const distBottom = window.innerHeight - r.bottom;
    const distRight = window.innerWidth - r.right;
    if (distBottom < -10 || distBottom > 96) return false;
    if (distRight < -10 || distRight > 96) return false;

    // Prefer body-level injects (extensions / Metrika), not in-app chrome
    const underApp = Boolean(el.closest?.(".app-shell, .sidebar, .main-panel, .auth-page"));
    if (underApp && !isMetrikaMarked(el)) return false;

    return true;
  } catch {
    return false;
  }
}

function hideEl(el) {
  if (!el || isOurUi(el)) return;
  el.classList?.add("gf-hide-corner-widget");
  try {
    el.style.setProperty("display", "none", "important");
    el.style.setProperty("visibility", "hidden", "important");
    el.style.setProperty("opacity", "0", "important");
    el.style.setProperty("pointer-events", "none", "important");
  } catch {
    /* ignore */
  }
  // Body-level Metrika/extension nodes: remove so they cannot reflow
  if (el.parentElement === document.body || isMetrikaMarked(el)) {
    try {
      el.remove();
    } catch {
      /* ignore */
    }
  }
}

function walkShadow(root, visit) {
  if (!root) return;
  const nodes = root.querySelectorAll ? root.querySelectorAll("*") : [];
  for (const el of nodes) {
    visit(el);
    if (el.shadowRoot) walkShadow(el.shadowRoot, visit);
  }
}

function stripUnauthorizedMetrikaUi() {
  if (canSeeMetrikaBadge() || !document.body) return;

  const visit = (el) => {
    if (isMetrikaMarked(el) || isCornerFloatingWidget(el)) hideEl(el);
  };

  visit(document.body);
  walkShadow(document.body, visit);

  // Iframes from Yandex in the corner
  for (const frame of document.querySelectorAll("iframe")) {
    if (isOurUi(frame)) continue;
    const src = frame.getAttribute("src") || frame.src || "";
    if (/yandex|metrika|metrica|mc\.yandex/i.test(src) || isCornerFloatingWidget(frame)) {
      hideEl(frame);
    }
  }
}

function watchMetrikaUi() {
  if (typeof MutationObserver === "undefined" || !document.body) return;
  if (badgeObserver) badgeObserver.disconnect();
  badgeObserver = new MutationObserver((mutations) => {
    if (canSeeMetrikaBadge()) return;
    let dirty = false;
    for (const m of mutations) {
      m.addedNodes.forEach((node) => {
        if (node.nodeType !== 1) return;
        dirty = true;
        if (isMetrikaMarked(node) || isCornerFloatingWidget(node)) hideEl(node);
        else stripUnauthorizedMetrikaUi();
      });
    }
    if (dirty) stripUnauthorizedMetrikaUi();
  });
  badgeObserver.observe(document.documentElement, { childList: true, subtree: true });

  if (scanTimer) clearInterval(scanTimer);
  let ticks = 0;
  scanTimer = setInterval(() => {
    ticks += 1;
    syncMetrikaBadge();
    if (ticks >= 40) {
      clearInterval(scanTimer);
      scanTimer = null;
    }
  }, 500);
}

/** Sync Metrika badge visibility with GameForge role. */
export function syncMetrikaBadge() {
  document.getElementById("gf-metrika-badge")?.remove();
  document.getElementById("gf-metrika-badge-css")?.remove();

  ensureGateCss();
  if (canSeeMetrikaBadge()) {
    document.documentElement.classList.remove("gf-hide-metrika-ui");
  } else {
    document.documentElement.classList.add("gf-hide-metrika-ui");
    stripUnauthorizedMetrikaUi();
  }
}

/** Initialize analytics once per page load. No-op without configured IDs. */
export function initAnalytics() {
  if (started) return;
  started = true;
  if (MEASUREMENT_ID && MEASUREMENT_ID.startsWith("G-")) {
    loadGtag(MEASUREMENT_ID);
  }
  // Always wire badge gate (even before Metrika script finishes), so role sync works.
  const boot = () => {
    syncMetrikaBadge();
    watchMetrikaUi();
  };
  if (METRIKA_ID) {
    loadMetrika(METRIKA_ID);
  }
  if (document.body) boot();
  else document.addEventListener("DOMContentLoaded", boot, { once: true });
}

/** Optional custom event helper (GA4). */
export function trackEvent(name, params = {}) {
  if (typeof window?.gtag !== "function") return;
  window.gtag("event", name, params);
}

export function getGaMeasurementId() {
  return MEASUREMENT_ID;
}

export function getYandexMetrikaId() {
  return METRIKA_ID;
}

// Auto-init when this module is imported
initAnalytics();
