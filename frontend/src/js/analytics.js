/**
 * Analytics — GA4 + Yandex Metrika when env IDs are set at build time.
 * Also captures first/last-touch UTM + LocForge from/pack into localStorage.
 */

const MEASUREMENT_ID = (import.meta.env.VITE_GA_MEASUREMENT_ID || "").trim();
const METRIKA_ID = String(import.meta.env.VITE_YANDEX_METRIKA_ID || "").trim();

const ATTR_KEY = "gf_attribution";
const ATTR_LAST_KEY = "gf_attribution_last";

let started = false;

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

function readStored(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "null");
  } catch {
    return null;
  }
}

/** Parse marketing params from current URL. */
export function parseMarketingParams(search = typeof location !== "undefined" ? location.search : "") {
  const params = new URLSearchParams(search);
  const pick = (k) => {
    const v = (params.get(k) || "").trim();
    return v || null;
  };
  const out = {
    utm_source: pick("utm_source"),
    utm_medium: pick("utm_medium"),
    utm_campaign: pick("utm_campaign"),
    utm_content: pick("utm_content"),
    utm_term: pick("utm_term"),
    from: pick("from"),
    pack: pick("pack"),
    gclid: pick("gclid"),
    ymclid: pick("ymclid"),
    landing_path: typeof location !== "undefined" ? `${location.pathname}` : null,
    captured_at: new Date().toISOString(),
  };
  const hasAny = Object.entries(out).some(
    ([k, v]) => v && k !== "captured_at" && k !== "landing_path",
  );
  return hasAny ? out : null;
}

/** Capture first-touch (once) + last-touch attribution from the URL. */
export function captureAttribution() {
  if (typeof window === "undefined") return null;
  const snap = parseMarketingParams();
  if (!snap) return getAttribution();

  localStorage.setItem(ATTR_LAST_KEY, JSON.stringify(snap));
  if (!readStored(ATTR_KEY)) {
    localStorage.setItem(ATTR_KEY, JSON.stringify(snap));
  }

  // Merge explicit from/pack into first-touch if missing
  const first = readStored(ATTR_KEY) || {};
  let dirty = false;
  if (snap.from && !first.from) {
    first.from = snap.from;
    dirty = true;
  }
  if (snap.pack && !first.pack) {
    first.pack = snap.pack;
    dirty = true;
  }
  if (dirty) localStorage.setItem(ATTR_KEY, JSON.stringify(first));
  return getAttribution();
}

/** First-touch attribution for signup payload. */
export function getAttribution() {
  return readStored(ATTR_KEY) || readStored(ATTR_LAST_KEY) || {};
}

/** Merge query from/pack into stored attribution (register page). */
export function mergeAttributionOverrides({ from, pack } = {}) {
  const cur = { ...getAttribution() };
  if (from) cur.from = String(from).slice(0, 64);
  if (pack) cur.pack = String(pack).slice(0, 32);
  cur.captured_at = cur.captured_at || new Date().toISOString();
  localStorage.setItem(ATTR_KEY, JSON.stringify(cur));
  localStorage.setItem(ATTR_LAST_KEY, JSON.stringify(cur));
  return cur;
}

/** Map landing pack=starter → billing plan loc_starter. */
export function packToPlan(pack) {
  const map = { starter: "loc_starter", indie: "loc_indie", studio: "loc_studio" };
  const key = String(pack || "").toLowerCase().replace(/^loc_/, "");
  return map[key] || null;
}

/** Initialize analytics once per page load. No-op without configured IDs. */
export function initAnalytics() {
  if (started) return;
  started = true;
  captureAttribution();
  if (MEASUREMENT_ID && MEASUREMENT_ID.startsWith("G-")) {
    loadGtag(MEASUREMENT_ID);
  }
  if (METRIKA_ID) {
    if (document.body) loadMetrika(METRIKA_ID);
    else document.addEventListener("DOMContentLoaded", () => loadMetrika(METRIKA_ID), { once: true });
  }
}

/**
 * Custom event helper (GA4 + Yandex Metrika reachGoal).
 * Goal names for Metrika: sign_up, locforge_cta, localize_success, loc_pack_click
 */
export function trackEvent(name, params = {}) {
  const payload = { ...params };
  const attr = getAttribution();
  if (attr.utm_source) payload.utm_source = attr.utm_source;
  if (attr.utm_campaign) payload.utm_campaign = attr.utm_campaign;
  if (attr.from) payload.from = attr.from;

  if (typeof window?.gtag === "function") {
    window.gtag("event", name, payload);
  }
  if (typeof window?.ym === "function" && METRIKA_ID) {
    try {
      window.ym(Number(METRIKA_ID), "reachGoal", name, payload);
    } catch {
      /* ignore */
    }
  }
}

export function getGaMeasurementId() {
  return MEASUREMENT_ID;
}

export function getYandexMetrikaId() {
  return METRIKA_ID;
}

initAnalytics();
