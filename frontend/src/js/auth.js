/**
 * Auth helpers and route guards.
 */

import { AuthAPI, clearTokens, isLoggedIn, setTokens } from "./api.js";

export function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = "/src/pages/login.html";
    return false;
  }
  return true;
}

export function redirectIfAuthed() {
  if (isLoggedIn()) {
    window.location.href = "/src/pages/dashboard.html";
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

export function logout() {
  clearTokens();
  window.location.href = "/src/pages/login.html";
}

export function currentUser() {
  try {
    return JSON.parse(localStorage.getItem("gf_user") || "null");
  } catch {
    return null;
  }
}
