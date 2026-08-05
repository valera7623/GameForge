/**
 * Auth helpers and route guards.
 */

import { AuthAPI, clearTokens, isLoggedIn, setTokens } from "./api.js";
import { t } from "./i18n.js";

/** Safe in-app path for post-login redirect (blocks open redirects). */
export function safeNextPath(raw, fallback = "/dashboard") {
  if (!raw || typeof raw !== "string") return fallback;
  const next = raw.trim();
  if (!next.startsWith("/") || next.startsWith("//") || next.includes("://")) return fallback;
  return next;
}

export function requireAuth() {
  if (!isLoggedIn()) {
    const next = encodeURIComponent(`${location.pathname}${location.search}`);
    window.location.href = `/login?next=${next}`;
    return false;
  }
  return true;
}

export function redirectIfAuthed() {
  if (isLoggedIn()) {
    const params = new URLSearchParams(location.search);
    window.location.href = safeNextPath(params.get("next"), "/dashboard");
  }
}

export async function login(email, password) {
  const tokens = await AuthAPI.login({ email, password });
  setTokens(tokens.access_token, tokens.refresh_token);
  const me = await AuthAPI.me();
  localStorage.setItem("gf_user", JSON.stringify(me));
  return me;
}

export async function register(email, password, full_name) {
  const tokens = await AuthAPI.register({ email, password, full_name });
  setTokens(tokens.access_token, tokens.refresh_token);
  const me = await AuthAPI.me();
  localStorage.setItem("gf_user", JSON.stringify(me));
  return me;
}

export async function logout() {
  try {
    await AuthAPI.logout();
  } catch {
    /* ignore */
  }
  clearTokens();
  window.location.href = "/login";
}

export function currentUser() {
  try {
    return JSON.parse(localStorage.getItem("gf_user") || "null");
  } catch {
    return null;
  }
}

export { t };
