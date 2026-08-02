/**
 * Light / dark theme toggle (persisted in localStorage).
 */

const KEY = "gf_theme";

export function getTheme() {
  const saved = localStorage.getItem(KEY);
  if (saved === "light" || saved === "dark") return saved;
  return "light";
}

export function applyTheme(theme) {
  const t = theme === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem(KEY, t);
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    const isDark = t === "dark";
    btn.setAttribute("aria-label", isDark ? "Switch to light theme" : "Switch to dark theme");
    btn.title = isDark ? "Светлая тема" : "Тёмная тема";
    btn.innerHTML = isDark ? "☀" : "☾";
  });
}

export function toggleTheme() {
  applyTheme(getTheme() === "dark" ? "light" : "dark");
}

export function bindThemeToggles(root = document) {
  root.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    if (btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      toggleTheme();
    });
  });
}

// Apply ASAP on module load (before paint when imported early)
applyTheme(getTheme());
