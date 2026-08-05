/**
 * Admin panel shell, guards, and API helpers.
 */

import { api } from "./api.js";
import { requireAuth, currentUser, logout } from "./auth.js";
import { applyDomI18n, escapeHtml, t } from "./app.js";
import { applyTheme, bindThemeToggles, getTheme } from "./theme.js";
import { getLang, setLang } from "./i18n.js";

const STAFF = new Set(["super_admin", "admin", "manager", "support"]);

const NAV = [
  ["", "admin.nav.dashboard", "/admin"],
  ["users", "admin.nav.users", "/admin/users"],
  ["generations", "admin.nav.generations", "/admin/generations"],
  ["subscriptions", "admin.nav.subscriptions", "/admin/subscriptions"],
  ["tools", "admin.nav.tools", "/admin/tools"],
  ["settings", "admin.nav.settings", "/admin/settings"],
];

export function isStaffRole(role) {
  return STAFF.has(role);
}

export function canWriteUsers(role) {
  return role === "super_admin" || role === "admin";
}

export function canWriteTools(role) {
  return role === "super_admin" || role === "admin";
}

export function canWriteSettings(role) {
  return role === "super_admin";
}

export function canWriteSubs(role) {
  return role === "super_admin" || role === "admin";
}

/** Guard: must be logged in + staff. Returns admin me payload or redirects. */
export async function requireStaff() {
  if (!requireAuth()) return null;
  const local = currentUser();
  if (!local || !isStaffRole(local.role)) {
    window.location.href = "/admin/login";
    return null;
  }
  try {
    const me = await AdminAPI.me();
    localStorage.setItem("gf_user", JSON.stringify({ ...local, role: me.role, permissions: me.permissions }));
    return me;
  } catch (err) {
    if (err.status === 403) {
      window.location.href = "/admin/login";
      return null;
    }
    throw err;
  }
}

export const AdminAPI = {
  me: () => api("/admin/auth/me"),
  dashboard: () => api("/admin/dashboard"),
  users: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return api(`/admin/users${q ? `?${q}` : ""}`);
  },
  user: (id) => api(`/admin/users/${id}`),
  updateUser: (id, body) => api(`/admin/users/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  blockUser: (id) => api(`/admin/users/${id}/block`, { method: "POST", body: "{}" }),
  unblockUser: (id) => api(`/admin/users/${id}/unblock`, { method: "POST", body: "{}" }),
  deleteUser: (id) => api(`/admin/users/${id}`, { method: "DELETE" }),
  setRole: (id, role) => api(`/admin/users/${id}/role`, { method: "POST", body: JSON.stringify({ role }) }),
  generations: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return api(`/admin/generations${q ? `?${q}` : ""}`);
  },
  generation: (id) => api(`/admin/generations/${id}`),
  generationStats: () => api("/admin/generations/stats"),
  userGenerations: (userId, params = {}) => {
    const q = new URLSearchParams(params).toString();
    return api(`/admin/generations/user/${userId}${q ? `?${q}` : ""}`);
  },
  subscriptions: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return api(`/admin/subscriptions${q ? `?${q}` : ""}`);
  },
  cancelSubscription: (id) => api(`/admin/subscriptions/${id}/cancel`, { method: "POST", body: "{}" }),
  tools: () => api("/admin/tools"),
  toggleTool: (name) => api(`/admin/tools/${name}/toggle`, { method: "POST", body: "{}" }),
  settings: () => api("/admin/settings"),
  saveSettings: (body) => api("/admin/settings", { method: "PUT", body: JSON.stringify(body) }),
};

function adminSidebar(active) {
  const nextLang = getLang() === "ru" ? "EN" : "RU";
  return `
    <aside class="sidebar admin-sidebar" aria-label="Admin">
      <div class="sidebar-top">
        <a class="brand" href="/admin"><span class="brand-mark" aria-hidden="true"></span><span class="brand-text">GameForge Admin</span></a>
        <div class="sidebar-controls">
          <button type="button" class="btn btn-icon" id="langBtn" title="${escapeHtml(t("lang.switch"))}">${nextLang}</button>
          <button type="button" class="btn btn-icon theme-toggle" data-theme-toggle aria-label="${escapeHtml(t("theme.toggle"))}">☾</button>
        </div>
      </div>
      <nav class="sidebar-nav">
        ${NAV.map(
          ([key, label, href]) =>
            `<a href="${href}" class="${active === key ? "active" : ""}">${escapeHtml(t(label))}</a>`
        ).join("")}
      </nav>
      <div class="spacer"></div>
      <a href="/dashboard" class="sidebar-docs">${escapeHtml(t("admin.nav.app"))}</a>
      <a href="#" id="logoutBtn" class="sidebar-logout">${escapeHtml(t("nav.signout"))}</a>
    </aside>
  `;
}

export function mountAdminShell(activeKey) {
  const shell = document.querySelector(".app-shell");
  if (!shell) return;
  shell.insertAdjacentHTML("afterbegin", adminSidebar(activeKey));
  applyDomI18n(shell);
  applyTheme(getTheme());
  bindThemeToggles(shell);
  document.getElementById("langBtn")?.addEventListener("click", () => {
    setLang(getLang() === "ru" ? "en" : "ru");
    location.reload();
  });
  document.getElementById("logoutBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    logout();
  });
}

export function pagerHtml(page, pageSize, total) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return `<div class="admin-pager">
    <button type="button" class="btn btn-ghost" data-page="${page - 1}" ${page <= 1 ? "disabled" : ""}>‹</button>
    <span>${page} / ${pages}</span>
    <button type="button" class="btn btn-ghost" data-page="${page + 1}" ${page >= pages ? "disabled" : ""}>›</button>
  </div>`;
}

export { escapeHtml, t, applyDomI18n };
