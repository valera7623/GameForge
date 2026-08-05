/**
 * Skeleton Screens — base API, navigation overlay, content hosts.
 * GameForge is an MPA; "router" integration intercepts same-origin navigations.
 */
import "./skeleton.css";
import { renderDashboardSkeleton } from "./skeleton-dashboard.js";
import { renderAgentsSkeleton, renderAgentsTableSkeleton } from "./skeleton-agents.js";
import { renderDetailSkeleton } from "./skeleton-detail.js";
import { renderListPageSkeleton, renderTableSkeleton } from "./skeleton-table.js";
import { renderCardSkeleton, renderStatCardsSkeleton } from "./skeleton-card.js";

export const SKELETON_SETTINGS = Object.freeze({
  min_display_ms: 450,
  max_display_ms: 3000,
  /** Hold overlay long enough for a paint before MPA unload */
  nav_hold_ms: 280,
  animation_duration: "1.5s",
  fade_duration: "0.3s",
});

const STORAGE_KEY = "gf_skeleton_nav";
const PREFETCH_LIMIT = 8;

/** @type {HTMLElement | null} */
let overlayEl = null;
/** @type {number | null} */
let overlayShownAt = null;
/** @type {ReturnType<typeof setTimeout> | null} */
let maxTimer = null;
/** @type {Set<string>} */
const prefetched = new Set();

/**
 * Resolve skeleton variant from a path (pathname).
 * @param {string} path
 * @returns {"dashboard"|"agents"|"detail"|"table"|"card"|"list"}
 */
export function resolveSkeletonVariant(path) {
  const p = (path || "/").split("?")[0].replace(/\/+$/, "") || "/";

  if (p === "/dashboard" || p === "/admin" || p === "/admin/dashboard") return "dashboard";
  if (p === "/agents" || p.startsWith("/tools")) return "agents";
  if (
    p.startsWith("/admin/users") ||
    p.startsWith("/admin/generations") ||
    p.startsWith("/admin/subscriptions") ||
    p.startsWith("/admin/content") ||
    p.startsWith("/admin/logs") ||
    p === "/projects" ||
    p === "/billing" ||
    p === "/history"
  ) {
    return "table";
  }
  if (
    /\/admin\/(user|generation|content-edit)\b/.test(p) ||
    /^\/(project|generation)\//.test(p) ||
    p === "/settings" ||
    p === "/profile"
  ) {
    return "detail";
  }
  if (p === "/" || p.startsWith("/pricing") || p.startsWith("/blog")) return "card";
  return "list";
}

/**
 * Build HTML for a named variant.
 * @param {string} variant
 * @param {object} [opts]
 * @returns {string}
 */
export function renderSkeletonVariant(variant, opts = {}) {
  switch (variant) {
    case "dashboard":
      return renderDashboardSkeleton(opts);
    case "agents":
      return renderAgentsSkeleton(opts);
    case "detail":
      return renderDetailSkeleton(opts);
    case "table":
      return renderListPageSkeleton({ rows: opts.rows ?? 8, ...opts });
    case "card":
      return `
        <div class="skeleton-base" aria-busy="true">
          <span class="skeleton-line lg w-50 skeleton-wave"></span>
          <span class="skeleton-line w-70 sm skeleton-wave" style="margin-bottom:1rem"></span>
          ${renderCardSkeleton({ count: opts.count ?? 6, height: opts.height ?? 100 })}
        </div>
      `;
    case "list":
    default:
      return renderListPageSkeleton(opts);
  }
}

/**
 * Low-level primitives as HTML helpers (for custom pages).
 */
export function skeletonLine(width = "w-70", extra = "") {
  return `<span class="skeleton-line ${width} skeleton-wave ${extra}"></span>`;
}

export function skeletonCircle(size = "") {
  return `<span class="skeleton-circle ${size} skeleton-wave"></span>`;
}

export function skeletonBox(height = 80, extra = "") {
  return `<div class="skeleton-box skeleton-wave ${extra}" style="height:${height}px;min-height:${height}px"></div>`;
}

export {
  renderDashboardSkeleton,
  renderAgentsSkeleton,
  renderAgentsTableSkeleton,
  renderDetailSkeleton,
  renderListPageSkeleton,
  renderTableSkeleton,
  renderCardSkeleton,
  renderStatCardsSkeleton,
};

function ensureOverlay() {
  if (overlayEl && document.body.contains(overlayEl)) return overlayEl;
  overlayEl = document.createElement("div");
  overlayEl.className = "skeleton-nav-overlay skeleton-base";
  overlayEl.id = "gfSkeletonNav";
  overlayEl.setAttribute("role", "status");
  overlayEl.setAttribute("aria-live", "polite");
  overlayEl.setAttribute("aria-busy", "true");
  overlayEl.hidden = true;
  document.body.appendChild(overlayEl);
  return overlayEl;
}

/**
 * Show full-page navigation skeleton.
 * @param {string} [href]
 * @param {object} [opts]
 */
export function showNavSkeleton(href, opts = {}) {
  const path = href ? new URL(href, location.origin).pathname : location.pathname;
  const variant = opts.variant || resolveSkeletonVariant(path);
  const el = ensureOverlay();
  const withChrome = opts.chrome !== false && !path.startsWith("/admin/login") && path !== "/login" && path !== "/register";

  const body = renderSkeletonVariant(variant, opts);
  if (withChrome) {
    el.innerHTML = `
      <div class="skeleton-nav-chrome">
        <aside class="skeleton-nav-side" aria-hidden="true">
          <span class="skeleton-line w-70 skeleton-wave" style="margin-bottom:1.5rem"></span>
          ${Array.from({ length: 7 }, () => `<span class="skeleton-line w-80 skeleton-wave"></span>`).join("")}
        </aside>
        <div class="skeleton-nav-main skeleton-nav-inner">${body}</div>
      </div>
    `;
  } else {
    el.innerHTML = `<div class="skeleton-nav-inner">${body}</div>`;
  }

  el.hidden = false;
  overlayShownAt = performance.now();
  document.documentElement.style.overflow = "hidden";

  if (maxTimer) clearTimeout(maxTimer);
  maxTimer = setTimeout(() => {
    /* keep overlay until navigation; max is a soft budget for in-page use */
  }, SKELETON_SETTINGS.max_display_ms);
}

/**
 * Hide navigation overlay (after min display time).
 * @returns {Promise<void>}
 */
export function hideNavSkeleton() {
  return new Promise((resolve) => {
    const boot = document.getElementById("gfSkeletonBoot") || window.__gfSkeletonBootEl;
    if (boot && boot.parentNode) {
      boot.remove();
      window.__gfSkeletonBootEl = null;
    }
    const el = overlayEl;
    if (!el || el.hidden) {
      resolve();
      return;
    }
    const elapsed = overlayShownAt ? performance.now() - overlayShownAt : SKELETON_SETTINGS.min_display_ms;
    const wait = Math.max(0, SKELETON_SETTINGS.min_display_ms - elapsed);
    setTimeout(() => {
      el.hidden = true;
      el.innerHTML = "";
      document.documentElement.style.overflow = "";
      overlayShownAt = null;
      if (maxTimer) {
        clearTimeout(maxTimer);
        maxTimer = null;
      }
      resolve();
    }, wait);
  });
}

/**
 * Mount a content skeleton into a host element.
 * @param {HTMLElement | string | null} host
 * @param {string} [variant]
 * @param {object} [opts]
 * @returns {() => Promise<void>} reveal function
 */
export function mountContentSkeleton(host, variant = "list", opts = {}) {
  const el = typeof host === "string" ? document.querySelector(host) : host;
  if (!el) {
    return async () => {};
  }
  const shownAt = performance.now();
  el.classList.add("skeleton-content-host");
  el.innerHTML = renderSkeletonVariant(variant, opts);
  el.hidden = false;
  el.setAttribute("aria-busy", "true");

  /** @param {string | HTMLElement} [htmlOrNode] */
  return async function reveal(htmlOrNode) {
    const elapsed = performance.now() - shownAt;
    const wait = Math.max(0, SKELETON_SETTINGS.min_display_ms - elapsed);
    await new Promise((r) => setTimeout(r, wait));
    el.classList.add("is-leaving");
    await new Promise((r) => setTimeout(r, parseFloat(SKELETON_SETTINGS.fade_duration) * 1000 * 0.5));
    if (typeof htmlOrNode === "string") {
      el.innerHTML = htmlOrNode;
    } else if (htmlOrNode instanceof HTMLElement) {
      el.replaceChildren(htmlOrNode);
    } else {
      el.innerHTML = "";
    }
    el.classList.remove("is-leaving");
    el.removeAttribute("aria-busy");
    el.classList.add("skeleton-base");
  };
}

/**
 * Mark destination for next page (session handoff).
 * @param {string} href
 */
export function markPendingNavigation(href) {
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        to: href,
        variant: resolveSkeletonVariant(new URL(href, location.origin).pathname),
        at: Date.now(),
      })
    );
  } catch {
    /* ignore quota / private mode */
  }
}

/**
 * Consume pending nav mark and optionally show overlay briefly until shell paints.
 * @returns {boolean}
 */
export function consumePendingNavigation() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    sessionStorage.removeItem(STORAGE_KEY);
    if (!raw) return false;
    const data = JSON.parse(raw);
    if (!data || Date.now() - (data.at || 0) > 8000) return false;
    showNavSkeleton(data.to || location.href, { variant: data.variant });
    return true;
  } catch {
    return false;
  }
}

function sameOriginNavUrl(anchor) {
  if (!(anchor instanceof HTMLAnchorElement)) return null;
  if (anchor.target && anchor.target !== "_self") return null;
  if (anchor.hasAttribute("download")) return null;
  const href = anchor.getAttribute("href");
  if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) return null;
  let url;
  try {
    url = new URL(anchor.href, location.origin);
  } catch {
    return null;
  }
  if (url.origin !== location.origin) return null;
  if (url.pathname === location.pathname && url.search === location.search && url.hash) return null;
  /* skip if only hash change on same page */
  if (url.pathname === location.pathname && url.search === location.search) return null;
  return url.href;
}

function prefetchHref(href) {
  if (!href || prefetched.has(href) || prefetched.size >= PREFETCH_LIMIT) return;
  if (!("connection" in navigator) || navigator.connection?.saveData) {
    /* still allow a few prefetches */
  }
  prefetched.add(href);
  const link = document.createElement("link");
  link.rel = "prefetch";
  link.href = href;
  link.as = "document";
  document.head.appendChild(link);
}

/**
 * Intercept in-app clicks, show skeleton, navigate.
 * Prefetch on hover (priority 7).
 */
export function initSkeletonNavigation(opts = {}) {
  if (typeof document === "undefined") return;
  if (document.documentElement.dataset.gfSkeletonNav === "1") return;
  document.documentElement.dataset.gfSkeletonNav = "1";

  document.documentElement.style.setProperty("--sk-pulse-duration", SKELETON_SETTINGS.animation_duration);
  document.documentElement.style.setProperty("--sk-fade-duration", SKELETON_SETTINGS.fade_duration);

  const root = opts.root || document;
  const skipSelector = opts.skipSelector || "[data-no-skeleton], [data-skeleton=\"off\"]";

  root.addEventListener(
    "click",
    (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = e.target instanceof Element ? e.target.closest("a[href]") : null;
      if (!a || a.matches(skipSelector) || a.closest(skipSelector)) return;
      const href = sameOriginNavUrl(a);
      if (!href) return;

      e.preventDefault();
      markPendingNavigation(href);
      showNavSkeleton(href);
      /* MPA: must wait for a real paint — 2 rAF is often invisible */
      setTimeout(() => {
        location.href = href;
      }, SKELETON_SETTINGS.nav_hold_ms);
    },
    true
  );

  root.addEventListener(
    "pointerenter",
    (e) => {
      const a = e.target instanceof Element ? e.target.closest("a[href]") : null;
      if (!a || a.matches(skipSelector)) return;
      const href = sameOriginNavUrl(a);
      if (href) prefetchHref(href);
    },
    true
  );

  window.addEventListener("pageshow", (ev) => {
    if (ev.persisted) hideNavSkeleton();
  });
}

/**
 * Call from mountShell / mountAdminShell after DOM is ready.
 * Hides leftover overlay and fades in main content.
 * @param {{ hadPending?: boolean }} [opts]
 */
export function finishPageSkeletonTransition(opts = {}) {
  const main = document.querySelector(".main-panel, .admin-main, main");
  if (main) {
    main.classList.add("skeleton-page-enter");
    main.addEventListener(
      "animationend",
      () => main.classList.remove("skeleton-page-enter"),
      { once: true }
    );
  }
  /* Keep nav skeleton visible longer when arriving from a transition */
  const delay = opts.hadPending ? SKELETON_SETTINGS.min_display_ms : 0;
  setTimeout(() => {
    hideNavSkeleton();
  }, delay);
}

/**
 * Convenience: init nav + consume pending mark.
 */
export function bootSkeletons() {
  const hadPending = consumePendingNavigation();
  initSkeletonNavigation();
  finishPageSkeletonTransition({ hadPending });
  return hadPending;
}
