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
  // Only target known Metrika badge/informer selectors — never blanket [class*="ym-"].
  style.textContent = canSeeMetrikaBadge()
    ? ""
    : `
    html.gf-hide-metrika-ui .gf-hide-corner-widget,
    html.gf-hide-metrika-ui a[href*="metrika.yandex"],
    html.gf-hide-metrika-ui a[href*="metrica.yandex"],
    html.gf-hide-metrika-ui a[href*="informer.yandex"],
    html.gf-hide-metrika-ui img.ym-advanced-informer,
    html.gf-hide-metrika-ui img[src*="informer.yandex"],
    html.gf-hide-metrika-ui img[src*="metrika.yandex"],
    html.gf-hide-metrika-ui .ym-advanced-informer,
    html.gf-hide-metrika-ui [class*="ym-informer"],
    html.gf-hide-metrika-ui [id*="ymWidget"],
    html.gf-hide-metrika-ui [id*="yandex_metrika"],
    html.gf-hide-metrika-ui .gf-metrika-badge {
      display: none !important;
      visibility: hidden !important;
      pointer-events: none !important;
      opacity: 0 !important;
    }
  `;
}

function isProtectedRoot(el) {
  if (!el || el.nodeType !== 1) return true;
  const tag = el.tagName;
  return tag === "HTML" || tag === "HEAD" || tag === "BODY" || tag === "SCRIPT" || tag === "STYLE" || tag === "LINK" || tag === "META";
}

function isOurUi(el) {
  if (!el || el.nodeType !== 1) return true;
  if (isProtectedRoot(el)) return true;
  if (el.id === "toast-live" || el.closest?.("#toast-live")) return true;
  if (el.classList?.contains("toast") || el.closest?.(".toast")) return true;
  if (el.classList?.contains("theme-toggle") || el.closest?.(".theme-toggle")) return true;
  if (el.classList?.contains("modal-overlay") || el.closest?.(".modal-overlay")) return true;
  if (el.closest?.(".sidebar, .app-shell, .main-panel, .auth-page, .bg-grid")) return true;
  return false;
}

function looksLikeTrackingPixel(el) {
  if (el.tagName !== "IMG") return false;
  const style = el.getAttribute("style") || "";
  return /left:\s*-9999px|position:\s*absolute/i.test(style) || (el.width <= 1 && el.height <= 1);
}

function isMetrikaBadgeNode(el) {
  if (!el || el.nodeType !== 1 || isProtectedRoot(el) || isOurUi(el)) return false;
  if (el.id === "gf-metrika-badge" || el.classList?.contains("gf-metrika-badge")) return true;

  const href = `${el.getAttribute?.("href") || ""}`;
  const src = `${el.getAttribute?.("src") || ""}`;
  const cls = typeof el.className === "string" ? el.className : "";
  const id = el.id || "";

  if (looksLikeTrackingPixel(el)) return false;

  if (/metrika\.yandex|metrica\.yandex|informer\.yandex/i.test(href)) return true;
  if (/informer\.yandex|metrika\.yandex/i.test(src)) return true;
  if (/ym-advanced-informer|ym-informer/i.test(`${cls} ${id}`)) return true;
  if (/ymWidget|yandex_metrika|YaMetrika/i.test(id)) return true;

  return false;
}

/** Small fixed widgets in the bottom-right corner, outside the app shell. */
function isCornerFloatingWidget(el) {
  if (!el || el.nodeType !== 1 || isOurUi(el) || isProtectedRoot(el)) return false;
  // Only consider direct (or near-direct) body injects — never app content
  if (el.parentElement !== document.body && el.parentElement?.parentElement !== document.body) {
    return isMetrikaBadgeNode(el);
  }
  try {
    const cs = window.getComputedStyle(el);
    if (cs.position !== "fixed") return false;

    const r = el.getBoundingClientRect();
    if (r.width < 18 || r.height < 18 || r.width > 160 || r.height > 160) return false;

    const distBottom = window.innerHeight - r.bottom;
    const distRight = window.innerWidth - r.right;
    if (distBottom < -4 || distBottom > 80) return false;
    if (distRight < -4 || distRight > 80) return false;

    return true;
  } catch {
    return false;
  }
}

function hideEl(el) {
  if (!el || isProtectedRoot(el) || isOurUi(el)) return;
  try {
    el.classList?.add("gf-hide-corner-widget");
    el.style.setProperty("display", "none", "important");
    el.style.setProperty("visibility", "hidden", "important");
    el.style.setProperty("pointer-events", "none", "important");
  } catch {
    /* ignore */
  }
  if (el.parentElement === document.body) {
    try {
      el.remove();
    } catch {
      /* ignore */
    }
  }
}

function stripUnauthorizedMetrikaUi() {
  if (canSeeMetrikaBadge() || !document.body) return;

  for (const el of [...document.body.children]) {
    if (isMetrikaBadgeNode(el) || isCornerFloatingWidget(el)) hideEl(el);
  }

  for (const el of document.body.querySelectorAll(
    "a[href*='metrika.yandex'], a[href*='informer.yandex'], img.ym-advanced-informer, img[src*='informer.yandex'], .ym-advanced-informer, [class*='ym-informer']",
  )) {
    if (!isOurUi(el)) hideEl(el);
  }
}

function watchMetrikaUi() {
  if (typeof MutationObserver === "undefined" || !document.body) return;
  if (badgeObserver) badgeObserver.disconnect();
  badgeObserver = new MutationObserver((mutations) => {
    if (canSeeMetrikaBadge()) return;
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (isProtectedRoot(node) || isOurUi(node)) continue;
        if (isMetrikaBadgeNode(node) || isCornerFloatingWidget(node)) hideEl(node);
      }
    }
  });
  badgeObserver.observe(document.body, { childList: true, subtree: true });

  if (scanTimer) clearInterval(scanTimer);
  let ticks = 0;
  scanTimer = setInterval(() => {
    ticks += 1;
    syncMetrikaBadge();
    if (ticks >= 20) {
      clearInterval(scanTimer);
      scanTimer = null;
    }
  }, 1000);
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

initAnalytics();
