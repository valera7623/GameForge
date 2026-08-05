/**
 * API client — cookie sessions + optional Bearer fallback, refresh mutex.
 */

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

let refreshPromise = null;

export function setTokens(_access, _refresh) {
  // Access/refresh live in httpOnly cookies set by the API.
  // Intentionally do not persist JWTs in localStorage.
}

export function clearTokens() {
  localStorage.removeItem("gf_user");
}

export function isLoggedIn() {
  return Boolean(localStorage.getItem("gf_user"));
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  const token = null;
  if (token) headers.Authorization = `Bearer ${token}`;

  const opts = { ...options, headers, credentials: "include" };
  let res = await fetch(`${API_BASE}${path}`, opts);

  if (res.status === 401 && !path.includes("/auth/refresh") && !path.includes("/auth/login")) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "include" });
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
    let msg;
    if (typeof detail === "string") {
      msg = detail;
    } else if (Array.isArray(detail)) {
      msg = detail
        .map((e) => (typeof e?.msg === "string" ? e.msg : JSON.stringify(e)))
        .join("; ");
    } else {
      msg = JSON.stringify(detail || data);
    }
    const err = new Error(msg || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

async function tryRefresh() {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!res.ok) {
        clearTokens();
        return false;
      }
      return true;
    } catch {
      clearTokens();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

export const AuthAPI = {
  register: (body) => api("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body) => api("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => api("/auth/logout", { method: "POST", body: "{}" }),
  me: () => api("/auth/me"),
  passwordReset: (email) =>
    api("/auth/password-reset/request", { method: "POST", body: JSON.stringify({ email }) }),
};

export const ProjectsAPI = {
  list: () => api("/projects"),
  create: (body) => api("/projects", { method: "POST", body: JSON.stringify(body) }),
  get: (id) => api(`/projects/${id}`),
  delete: (id) => api(`/projects/${id}`, { method: "DELETE" }),
  exportUrl: (id) => `${API_BASE}/projects/${id}/export`,
};

export const ToolsAPI = {
  level: (body) => api("/level-designer", { method: "POST", body: JSON.stringify(body) }),
  quest: (body) => api("/quest-generator", { method: "POST", body: JSON.stringify(body) }),
  character: (body) => api("/character-creator", { method: "POST", body: JSON.stringify(body) }),
  sound: (body) => api("/sound-designer", { method: "POST", body: JSON.stringify(body) }),
  playtest: (body) => api("/playtester", { method: "POST", body: JSON.stringify(body) }),
  localize: (body) => api("/localization", { method: "POST", body: JSON.stringify(body) }),
  balance: (body) => api("/game-balancer", { method: "POST", body: JSON.stringify(body) }),
  levelAnalyze: (body) => api("/level-analyzer", { method: "POST", body: JSON.stringify(body) }),
  levelCompare: (body) => api("/level-analyzer/compare", { method: "POST", body: JSON.stringify(body) }),
  storeDescription: (body) => api("/store-description", { method: "POST", body: JSON.stringify(body) }),
  playtestAnalyze: (body) => api("/playtest-analyzer", { method: "POST", body: JSON.stringify(body) }),
  trailerScript: (body) => api("/trailer-script", { method: "POST", body: JSON.stringify(body) }),
  reviewAnalyze: (body) => api("/review-analyzer", { method: "POST", body: JSON.stringify(body) }),
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
  getGeneration: (id) => api(`/generations/${id}`),
  deleteGeneration: (id) => api(`/generations/${id}`, { method: "DELETE" }),
  leaderboard: () => api("/leaderboard"),
};

export const BillingAPI = {
  plans: () => api("/billing/plans"),
  checkout: (plan) => api("/billing/checkout", { method: "POST", body: JSON.stringify({ plan }) }),
  subscription: () => api("/billing/subscription"),
  portal: () => api("/billing/portal", { method: "POST", body: "{}" }),
  cancel: () => api("/billing/cancel", { method: "POST", body: "{}" }),
};

/** Poll async Celery-backed generation until completed/failed. */
export async function pollGeneration(id, { intervalMs = 1500, timeoutMs = 180000, onTick } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const gen = await DashboardAPI.getGeneration(id);
    if (onTick) onTick(gen);
    if (gen.status === "completed" || gen.status === "failed") return gen;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Generation timed out");
}

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
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
