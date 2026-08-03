/**
 * Google Analytics 4 — enabled when VITE_GA_MEASUREMENT_ID is set (e.g. G-XXXXXXXX).
 */

const MEASUREMENT_ID = (import.meta.env.VITE_GA_MEASUREMENT_ID || "").trim();

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

/** Initialize GA4 once per page load. No-op without a measurement ID. */
export function initAnalytics() {
  if (started) return;
  started = true;
  if (!MEASUREMENT_ID || !MEASUREMENT_ID.startsWith("G-")) return;
  loadGtag(MEASUREMENT_ID);
}

/** Optional custom event helper. */
export function trackEvent(name, params = {}) {
  if (typeof window?.gtag !== "function") return;
  window.gtag("event", name, params);
}

export function getGaMeasurementId() {
  return MEASUREMENT_ID;
}

// Auto-init when this module is imported
initAnalytics();
