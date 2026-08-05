/**
 * Shared UI helpers + landing page boot.
 */

import { applyTheme, bindThemeToggles, getTheme } from "./theme.js";
import { applyDomI18n, getLang, setLang, t } from "./i18n.js";
import { getDocsUrl } from "./docs.js";
import { initAnalytics } from "./analytics.js";

initAnalytics();

export { t, getLang, applyDomI18n };


export function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function toast(message, isError = false) {
  let region = document.getElementById("toast-live");
  if (!region) {
    region = document.createElement("div");
    region.id = "toast-live";
    region.setAttribute("aria-live", "polite");
    region.setAttribute("role", "status");
    region.style.cssText = "position:fixed;bottom:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;";
    document.body.appendChild(region);
  }
  const el = document.createElement("div");
  el.className = `toast${isError ? " error" : ""}`;
  el.textContent = message;
  region.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

export function setLoading(el, on) {
  if (!el) return;
  el.classList.toggle("visible", on);
}

export function statusBadge(status) {
  const map = {
    completed: "badge-ok",
    processing: "badge-pending",
    pending: "badge-pending",
    failed: "badge-fail",
  };
  return `<span class="badge ${map[status] || "badge-pending"}">${escapeHtml(status)}</span>`;
}

export function showModal({ title, fields, confirmLabel = "OK", onSubmit }) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.innerHTML = `
      <div class="modal-card">
        <h2 id="modal-title">${escapeHtml(title)}</h2>
        <form id="modalForm" class="form-grid">
          ${fields
            .map((f) => {
              if (f.type === "select") {
                return `<label>${escapeHtml(f.label)}
                  <select name="${escapeHtml(f.name)}" required>
                    ${(f.options || []).map((o) => `<option value="${escapeHtml(o.value)}">${escapeHtml(o.label)}</option>`).join("")}
                  </select>
                </label>`;
              }
              return `<label>${escapeHtml(f.label)}
                <input name="${escapeHtml(f.name)}" type="${escapeHtml(f.type || "text")}" value="${escapeHtml(f.value || "")}" ${f.required === false ? "" : "required"} />
              </label>`;
            })
            .join("")}
          <div class="form-row" style="justify-content:flex-end;gap:0.5rem;margin-top:0.5rem">
            <button type="button" class="btn" data-cancel>${escapeHtml(t("common.cancel"))}</button>
            <button type="submit" class="btn btn-primary">${escapeHtml(confirmLabel)}</button>
          </div>
        </form>
      </div>`;
    document.body.appendChild(overlay);
    const form = overlay.querySelector("#modalForm");
    const first = form.querySelector("input,select");
    first?.focus();
    const close = (val) => {
      overlay.remove();
      resolve(val);
    };
    overlay.querySelector("[data-cancel]").addEventListener("click", () => close(null));
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close(null);
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const data = Object.fromEntries(fd.entries());
      if (onSubmit) await onSubmit(data);
      close(data);
    });
  });
}

const ROUTES = [
  ["dashboard", "nav.dashboard"],
  ["level-designer", "nav.level"],
  ["quest-generator", "nav.quest"],
  ["texture-upscaler", "nav.texture"],
  ["character-creator", "nav.character"],
  ["sound-designer", "nav.sound"],
  ["playtester", "nav.playtester"],
  ["localization", "nav.localization"],
  ["game-balancer", "nav.balancer"],
  ["level-analyzer", "nav.level_analyzer"],
  ["team", "nav.team"],
];

const TOOL_ROUTES = [
  ["level-designer", "nav.level", "dash.tool.level_d"],
  ["quest-generator", "nav.quest", "dash.tool.quest_d"],
  ["texture-upscaler", "nav.texture", "dash.tool.texture_d"],
  ["character-creator", "nav.character", "dash.tool.character_d"],
  ["sound-designer", "nav.sound", "dash.tool.sound_d"],
  ["playtester", "nav.playtester", "dash.tool.play_d"],
  ["localization", "nav.localization", "dash.tool.loc_d"],
  ["game-balancer", "nav.balancer", "dash.tool.bal_d"],
  ["level-analyzer", "nav.level_analyzer", "dash.tool.lana_d"],
];

export function sidebarHTML(active) {
  const activeKey = (active || "").replace(/\.html$/, "");
  const nextLang = getLang() === "ru" ? "EN" : "RU";
  let adminLink = "";
  let userEmail = "";
  try {
    const raw = localStorage.getItem("gf_user");
    const u = raw ? JSON.parse(raw) : null;
    if (u?.email) userEmail = String(u.email);
    const staff = u && ["super_admin", "admin", "manager", "support"].includes(u.role);
    if (staff) {
      adminLink = `<a href="/admin">${t("nav.admin")}</a>`;
    }
  } catch {
    /* ignore */
  }
  const userBlock = userEmail
    ? `<div class="sidebar-user" title="${escapeHtml(userEmail)}">${escapeHtml(userEmail)}</div>`
    : "";
  return `
    <aside class="sidebar" aria-label="Main">
      <div class="sidebar-top">
        <a class="brand" href="/"><span class="brand-mark" aria-hidden="true"></span><span class="brand-text">GameForge</span></a>
        <div class="sidebar-controls">
          <button type="button" class="btn btn-icon" id="langBtn" aria-label="${t("lang.switch")}" title="${t("lang.switch")}">${nextLang}</button>
          <button type="button" class="btn btn-icon theme-toggle" data-theme-toggle aria-label="${t("theme.toggle")}">☾</button>
          <button type="button" class="btn btn-icon nav-toggle" id="navToggle" aria-expanded="false" aria-controls="sidebarDrawer" aria-label="${t("nav.menu")}">
            <span class="nav-toggle-bars" aria-hidden="true"></span>
          </button>
        </div>
      </div>
      <div class="sidebar-drawer" id="sidebarDrawer">
        <nav class="sidebar-nav sidebar-nav-mobile" aria-label="${t("nav.menu")}">
          <a href="/dashboard" class="${activeKey === "dashboard" ? "active" : ""}">${t("nav.dashboard")}</a>
          <a href="/team" class="${activeKey === "team" ? "active" : ""}">${t("nav.team")}</a>
          ${adminLink}
          <a href="${getDocsUrl()}" target="_blank" rel="noopener noreferrer">${t("nav.docs")}</a>
        </nav>
        <div class="sidebar-tools">
          <p class="sidebar-tools-title">${t("dash.launch")}</p>
          ${TOOL_ROUTES.map(
            ([path, key, descKey]) =>
              `<a href="/${path}" class="sidebar-tool-link${activeKey === path ? " active" : ""}"><strong>${t(key)}</strong><span>${t(descKey)}</span></a>`
          ).join("")}
        </div>
        <nav class="sidebar-nav sidebar-nav-desktop" aria-label="${t("nav.menu")}">
          ${ROUTES.map(
            ([path, key]) =>
              `<a href="/${path}" class="${activeKey === path ? "active" : ""}">${t(key)}</a>`
          ).join("")}
          ${adminLink}
        </nav>
        <div class="spacer"></div>
        ${userBlock}
        <a href="${getDocsUrl()}" target="_blank" rel="noopener noreferrer" class="sidebar-docs">${t("nav.docs")}</a>
        <a href="#" id="logoutBtn" class="sidebar-logout">${t("nav.signout")}</a>
      </div>
    </aside>
    <div class="nav-backdrop" id="navBackdrop" hidden></div>
  `;
}

function closeMobileNav() {
  const sidebar = document.querySelector(".sidebar");
  const toggle = document.getElementById("navToggle");
  const backdrop = document.getElementById("navBackdrop");
  if (!sidebar) return;
  sidebar.classList.remove("is-open");
  document.body.classList.remove("nav-open");
  toggle?.setAttribute("aria-expanded", "false");
  toggle?.setAttribute("aria-label", t("nav.menu"));
  if (backdrop) backdrop.hidden = true;
}

function openMobileNav() {
  const sidebar = document.querySelector(".sidebar");
  const toggle = document.getElementById("navToggle");
  const backdrop = document.getElementById("navBackdrop");
  if (!sidebar) return;
  sidebar.classList.add("is-open");
  document.body.classList.add("nav-open");
  toggle?.setAttribute("aria-expanded", "true");
  toggle?.setAttribute("aria-label", t("nav.close"));
  if (backdrop) backdrop.hidden = false;
}

function bindMobileNav() {
  const toggle = document.getElementById("navToggle");
  const backdrop = document.getElementById("navBackdrop");
  const drawer = document.getElementById("sidebarDrawer");
  toggle?.addEventListener("click", () => {
    const sidebar = document.querySelector(".sidebar");
    if (sidebar?.classList.contains("is-open")) closeMobileNav();
    else openMobileNav();
  });
  backdrop?.addEventListener("click", closeMobileNav);
  drawer?.querySelectorAll("a").forEach((a) => {
    a.addEventListener("click", () => {
      if (window.matchMedia("(max-width: 860px)").matches) closeMobileNav();
    });
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMobileNav();
  });
  window.addEventListener("resize", () => {
    if (!window.matchMedia("(max-width: 860px)").matches) closeMobileNav();
  });
}

export function mountShell(activePage) {
  const shell = document.querySelector(".app-shell");
  if (!shell) return;
  const main = shell.querySelector(".main-panel");
  if (main) main.setAttribute("role", "main");
  shell.insertAdjacentHTML("afterbegin", sidebarHTML(activePage));
  applyDomI18n(shell);
  applyTheme(getTheme());
  bindThemeToggles(shell);
  bindMobileNav();
  document.getElementById("langBtn")?.addEventListener("click", () => {
    setLang(getLang() === "ru" ? "en" : "ru");
    location.reload();
  });
  document.getElementById("logoutBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    import("./auth.js").then((m) => m.logout());
  });
  return main;
}

document.addEventListener("DOMContentLoaded", () => {
  applyDomI18n(document);
  applyTheme(getTheme());
  bindThemeToggles();

  const glow = document.querySelector(".bg-glow");
  if (glow) {
    window.addEventListener("pointermove", (e) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 30;
      const y = (e.clientY / window.innerHeight - 0.5) * 30;
      glow.style.transform = `translate(${x}px, ${y}px)`;
    });
  }
});
