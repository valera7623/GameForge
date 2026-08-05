/**
 * Analytics — GA4 + Yandex Metrika when env IDs are set at build time.
 *
 * Tracking runs for all visitors. The native Metrika corner badge/informer
 * is visible only to GameForge admin and super_admin.
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
  // Hide native Metrika UI for non-staff. Staff keeps the original badge.
  style.textContent = canSeeMetrikaBadge()
    ? ""
    : `
    html.gf-hide-metrika-ui a[href*="metrika.yandex"],
    html.gf-hide-metrika-ui a[href*="metrica.yandex"],
    html.gf-hide-metrika-ui a[href*="informer.yandex"],
    html.gf-hide-metrika-ui img[src*="informer.yandex"],
    html.gf-hide-metrika-ui img[src*="metrika.yandex"],
    html.gf-hide-metrika-ui img[src*="mc.yandex"],
    html.gf-hide-metrika-ui iframe[src*="metrika.yandex"],
    html.gf-hide-metrika-ui iframe[src*="mc.yandex.ru"],
    html.gf-hide-metrika-ui iframe[src*="mc.yandex.com"],
    html.gf-hide-metrika-ui .ym-advanced-informer,
    html.gf-hide-metrika-ui [class*="ym-informer"],
    html.gf-hide-metrika-ui [class*="metrika"],
    html.gf-hide-metrika-ui [id*="ymWidget"],
    html.gf-hide-metrika-ui [id*="yandex_metrika"],
    html.gf-hide-metrika-ui [id*="YaMetrika"],
    html.gf-hide-metrika-ui .gf-metrika-badge {
      display: none !important;
      visibility: hidden !important;
      pointer-events: none !important;
      opacity: 0 !important;
    }
  `;
}

function looksLikeTrackingPixel(el) {
  if (el.tagName !== "IMG") return false;
  const style = el.getAttribute("style") || "";
  return /left:\s*-9999px|position:\s*absolute/i.test(style) || (el.width <= 1 && el.height <= 1);
}

function isMetrikaUiElement(el) {
  if (!el || el.nodeType !== 1) return false;
  if (el.id === "gf-metrika-badge" || el.classList?.contains("gf-metrika-badge")) return true;

  const href = `${el.getAttribute?.("href") || ""} ${el.href || ""}`;
  const src = `${el.getAttribute?.("src") || ""} ${el.src || ""}`;
  const cls = `${el.className || ""}`;
  const id = `${el.id || ""}`;
  const title = `${el.getAttribute?.("title") || ""} ${el.getAttribute?.("aria-label") || ""}`;

  if (looksLikeTrackingPixel(el)) return false;

  if (/metrika\.yandex|metrica\.yandex|informer\.yandex/i.test(href)) return true;
  if (/informer\.yandex|metrika\.yandex|mc\.yandex\.(ru|com)\/(?!watch\/)/i.test(src)) return true;
  if (/ym-advanced-informer|ym-informer|metrika-informer/i.test(cls)) return true;
  if (/ymWidget|yandex_metrika|YaMetrika/i.test(id)) return true;
  if (/Яндекс\.?\s*Метрик|Yandex\.?\s*Metrica/i.test(title)) return true;

  try {
    const bg = window.getComputedStyle(el).backgroundImage || "";
    if (/informer\.yandex|metrika\.yandex|mc\.yandex/i.test(bg)) return true;
  } catch {
    /* ignore */
  }

  // Corner floating widgets often wrap the informer without obvious attrs on the root.
  try {
    const cs = window.getComputedStyle(el);
    if (cs.position === "fixed") {
      const bottom = Number.parseFloat(cs.bottom);
      const right = Number.parseFloat(cs.right);
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      if (
        Number.isFinite(bottom) &&
        Number.isFinite(right) &&
        bottom >= 0 &&
        bottom < 100 &&
        right >= 0 &&
        right < 100 &&
        w > 20 &&
        w < 140 &&
        h > 20 &&
        h < 140
      ) {
        const html = (el.outerHTML || "").slice(0, 2000);
        if (/metrika|metrica|informer\.yandex|mc\.yandex|Яндекс/i.test(html)) return true;
        // Circular badge with yandex child img/svg/link
        if (el.querySelector?.('a[href*="yandex"], img[src*="yandex"], iframe[src*="yandex"]')) return true;
      }
    }
  } catch {
    /* ignore */
  }

  return false;
}

function stripUnauthorizedMetrikaUi(root = document.body) {
  if (!root || canSeeMetrikaBadge()) return;
  const walk = root.querySelectorAll ? [root, ...root.querySelectorAll("*")] : [root];
  for (const el of walk) {
    if (!isMetrikaUiElement(el)) continue;
    // Prefer removing the outermost fixed wrapper when possible
    let target = el;
    const parent = el.parentElement;
    if (parent && parent !== document.body && isMetrikaUiElement(parent)) target = parent;
    target.remove?.();
  }
}

function watchMetrikaUi() {
  if (typeof MutationObserver === "undefined" || !document.body) return;
  if (badgeObserver) badgeObserver.disconnect();
  badgeObserver = new MutationObserver((mutations) => {
    if (canSeeMetrikaBadge()) return;
    for (const m of mutations) {
      m.addedNodes.forEach((node) => {
        if (node.nodeType !== 1) return;
        if (isMetrikaUiElement(node)) {
          node.remove?.();
          return;
        }
        stripUnauthorizedMetrikaUi(node);
      });
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

/** Sync native Metrika badge visibility with GameForge role. */
export function syncMetrikaBadge() {
  // Always remove our temporary red badge if any leftover remains
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
  if (METRIKA_ID) {
    loadMetrika(METRIKA_ID);
    const boot = () => {
      syncMetrikaBadge();
      watchMetrikaUi();
    };
    if (document.body) boot();
    else document.addEventListener("DOMContentLoaded", boot, { once: true });
  }
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
