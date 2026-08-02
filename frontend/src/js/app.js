/**
 * Shared UI helpers + landing page boot.
 */

import { applyTheme, bindThemeToggles, getTheme } from "./theme.js";

export function toast(message, isError = false) {
  const el = document.createElement("div");
  el.className = `toast${isError ? " error" : ""}`;
  el.textContent = message;
  document.body.appendChild(el);
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
  return `<span class="badge ${map[status] || "badge-pending"}">${status}</span>`;
}

export function sidebarHTML(active) {
  const items = [
    ["dashboard.html", "Dashboard"],
    ["level-designer.html", "Level Designer"],
    ["quest-generator.html", "Quest Generator"],
    ["texture-upscaler.html", "Texture Upscaler"],
    ["character-creator.html", "Character Creator"],
    ["sound-designer.html", "Sound Designer"],
    ["playtester.html", "Playtester"],
    ["localization.html", "Localization"],
    ["team.html", "Team"],
  ];
  return `
    <aside class="sidebar">
      <div class="sidebar-top">
        <a class="brand" href="/">GameForge</a>
        <button type="button" class="btn btn-icon theme-toggle" data-theme-toggle aria-label="Toggle theme">☾</button>
      </div>
      ${items
        .map(
          ([href, label]) =>
            `<a href="/src/pages/${href}" class="${active === href ? "active" : ""}">${label}</a>`
        )
        .join("")}
      <div class="spacer"></div>
      <a href="#" id="logoutBtn">Sign out</a>
    </aside>
  `;
}

export function mountShell(activePage) {
  const shell = document.querySelector(".app-shell");
  if (!shell) return;
  const main = shell.querySelector(".main-panel");
  shell.insertAdjacentHTML("afterbegin", sidebarHTML(activePage));
  applyTheme(getTheme());
  bindThemeToggles(shell);
  document.getElementById("logoutBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    import("./auth.js").then((m) => m.logout());
  });
  return main;
}

document.addEventListener("DOMContentLoaded", () => {
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
