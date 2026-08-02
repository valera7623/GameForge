/**
 * API client for GameForge backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

function getToken() {
  return localStorage.getItem("gf_access_token");
}

function getRefresh() {
  return localStorage.getItem("gf_refresh_token");
}

export function setTokens(access, refresh) {
  localStorage.setItem("gf_access_token", access);
  if (refresh) localStorage.setItem("gf_refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("gf_access_token");
  localStorage.removeItem("gf_refresh_token");
  localStorage.removeItem("gf_user");
}

export function isLoggedIn() {
  return Boolean(getToken());
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && getRefresh()) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers.Authorization = `Bearer ${getToken()}`;
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    }
  }

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }

  if (!res.ok) {
    const detail = data?.detail;
    const msg = typeof detail === "string" ? detail : JSON.stringify(detail || data);
    const err = new Error(msg || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

async function tryRefresh() {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh?refresh_token=${encodeURIComponent(getRefresh())}`, {
      method: "POST",
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export const AuthAPI = {
  register: (body) => api("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body) => api("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => api("/auth/me"),
  passwordReset: (email) =>
    api("/auth/password-reset/request", { method: "POST", body: JSON.stringify({ email }) }),
};

export const ProjectsAPI = {
  list: () => api("/projects"),
  create: (body) => api("/projects", { method: "POST", body: JSON.stringify(body) }),
  get: (id) => api(`/projects/${id}`),
  exportUrl: (id) => `${API_BASE}/projects/${id}/export`,
};

export const ToolsAPI = {
  level: (body) => api("/level-designer", { method: "POST", body: JSON.stringify(body) }),
  quest: (body) => api("/quest-generator", { method: "POST", body: JSON.stringify(body) }),
  character: (body) => api("/character-creator", { method: "POST", body: JSON.stringify(body) }),
  sound: (body) => api("/sound-designer", { method: "POST", body: JSON.stringify(body) }),
  playtest: (body) => api("/playtester", { method: "POST", body: JSON.stringify(body) }),
  localize: (body) => api("/localization", { method: "POST", body: JSON.stringify(body) }),
  upscale: async (file, scale, enhance, projectId) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("scale", String(scale));
    fd.append("enhance", String(enhance));
    if (projectId) fd.append("project_id", projectId);
    return api("/texture-upscaler", { method: "POST", body: fd, headers: {} });
  },
};

export const DashboardAPI = {
  stats: () => api("/dashboard"),
  generations: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return api(`/generations${q ? `?${q}` : ""}`);
  },
  leaderboard: () => api("/leaderboard"),
};

export const BillingAPI = {
  plans: () => api("/billing/plans"),
  checkout: (plan) => api("/billing/checkout", { method: "POST", body: JSON.stringify({ plan }) }),
  subscription: () => api("/billing/subscription"),
};

export function downloadJSON(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export function downloadText(filename, text, mime = "text/plain") {
  const blob = new Blob([text], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export async function downloadAuthed(url, filename) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
