/**
 * Analytics — GA4 + Yandex Metrika when env IDs are set at build time.
 *
 * Tracking runs for all visitors. The Metrika corner badge / informer is
 * only shown to platform admin and super_admin (GameForge roles).
 */

const MEASUREMENT_ID = (import.meta.env.VITE_GA_MEASUREMENT_ID || "").trim();
const METRIKA_ID = String(import.meta.env.VITE_YANDEX_METRIKA_ID || "").trim();

let started = false;
let badgeObserver = null;

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

function canOpenMetrikaBadge() {
  try {
    const u = JSON.parse(localStorage.getItem("gf_user") || "null");
    return Boolean(u && (u.role === "super_admin" || u.role === "admin"));
  } catch {
    return false;
  }
}

function isMetrikaUiNode(node) {
  if (!node || node.nodeType !== 1) return false;
  if (node.id === "gf-metrika-badge") return false;
  const el = /** @type {HTMLElement} */ (node);
  if (el.closest?.("#gf-metrika-badge")) return false;

  const href = (el.getAttribute?.("href") || el.href || "").toString();
  const src = (el.getAttribute?.("src") || el.src || "").toString();
  if (/metrika\.yandex|metrica\.yandex|informer\.yandex/i.test(href)) return true;
  if (/informer\.yandex\.ru|mc\.yandex\.(ru|com)\/(?:watch|metrika)/i.test(src)) {
    // Keep the 1x1 tracking pixel in noscript out of the corner UI path
    if (el.tagName === "IMG" && /left:\s*-9999px|position:\s*absolute/i.test(el.getAttribute("style") || "")) {
      return false;
    }
    if (el.tagName === "IMG" && /informer\.yandex/i.test(src)) return true;
  }
  if (el.classList?.contains("ym-advanced-informer")) return true;
  if (el.id === "ymWidget" || el.id === "yandex_metrika_informer") return true;
  return false;
}

function stripUnauthorizedMetrikaUi(root = document.body) {
  if (!root || canOpenMetrikaBadge()) return;
  const candidates = root.querySelectorAll?.(
    'a[href*="metrika.yandex"], a[href*="metrica.yandex"], a[href*="informer.yandex"], img[src*="informer.yandex.ru"], .ym-advanced-informer, #ymWidget, #yandex_metrika_informer'
  );
  candidates?.forEach((el) => {
    if (el.id === "gf-metrika-badge" || el.closest?.("#gf-metrika-badge")) return;
    el.remove();
  });
}

function ensureHideStyle() {
  if (document.getElementById("gf-metrika-gate-css")) return;
  const style = document.createElement("style");
  style.id = "gf-metrika-gate-css";
  // Hide foreign Metrika informers for everyone; admins get our controlled badge instead.
  style.textContent = `
    a[href*="metrika.yandex.ru"]:not(#gf-metrika-badge),
    a[href*="metrica.yandex"]:not(#gf-metrika-badge),
    a[href*="informer.yandex"],
    img[src*="informer.yandex.ru"],
    .ym-advanced-informer,
    #ymWidget,
    #yandex_metrika_informer {
      display: none !important;
      visibility: hidden !important;
      pointer-events: none !important;
    }
  `;
  document.head.appendChild(style);
}

function mountAdminMetrikaBadge(id) {
  if (!canOpenMetrikaBadge() || !id) return;
  let badge = document.getElementById("gf-metrika-badge");
  if (badge) return;
  badge = document.createElement("a");
  badge.id = "gf-metrika-badge";
  badge.className = "gf-metrika-badge";
  badge.href = `https://metrika.yandex.ru/dashboard?id=${encodeURIComponent(id)}`;
  badge.target = "_blank";
  badge.rel = "noopener noreferrer";
  badge.title = "Yandex Metrika";
  badge.setAttribute("aria-label", "Yandex Metrika");
  badge.innerHTML =
    '<span class="gf-metrika-badge-mark" aria-hidden="true">Я</span><span class="gf-metrika-badge-text">Метрика</span>';
  document.body.appendChild(badge);

  if (!document.getElementById("gf-metrika-badge-css")) {
    const style = document.createElement("style");
    style.id = "gf-metrika-badge-css";
    style.textContent = `
      .gf-metrika-badge {
        position: fixed;
        right: 0.85rem;
        bottom: 0.85rem;
        z-index: 9998;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.45rem 0.7rem;
        border-radius: 999px;
        background: #fc3f1d;
        color: #fff !important;
        text-decoration: none !important;
        font: 600 0.75rem/1 "IBM Plex Sans", system-ui, sans-serif;
        box-shadow: 0 6px 18px rgba(0,0,0,.18);
        opacity: 0.92;
      }
      .gf-metrika-badge:hover { opacity: 1; }
      .gf-metrika-badge-mark {
        display: inline-grid;
        place-items: center;
        width: 1.15rem;
        height: 1.15rem;
        border-radius: 50%;
        background: rgba(255,255,255,.2);
        font-weight: 700;
      }
    `;
    document.head.appendChild(style);
  }
}

function removeAdminMetrikaBadge() {
  document.getElementById("gf-metrika-badge")?.remove();
}

function watchMetrikaUi() {
  if (badgeObserver || typeof MutationObserver === "undefined" || !document.body) return;
  badgeObserver = new MutationObserver((mutations) => {
    if (canOpenMetrikaBadge()) return;
    for (const m of mutations) {
      m.addedNodes.forEach((node) => {
        if (isMetrikaUiNode(node)) {
          /** @type {HTMLElement} */ (node).remove?.();
          return;
        }
        if (node.nodeType === 1) stripUnauthorizedMetrikaUi(/** @type {HTMLElement} */ (node));
      });
    }
  });
  badgeObserver.observe(document.body, { childList: true, subtree: true });
}

/** Sync badge visibility with current GameForge session role. */
export function syncMetrikaBadge() {
  ensureHideStyle();
  stripUnauthorizedMetrikaUi();
  if (canOpenMetrikaBadge() && METRIKA_ID) {
    mountAdminMetrikaBadge(METRIKA_ID);
  } else {
    removeAdminMetrikaBadge();
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
