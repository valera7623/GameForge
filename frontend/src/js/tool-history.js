/**
 * Recent generations strip for tool pages.
 */

import { DashboardAPI } from "./api.js";
import { escapeHtml, statusBadge } from "./app.js";
import { t } from "./i18n.js";

export async function mountToolHistory(tool, containerId = "toolHistory") {
  const el = document.getElementById(containerId);
  if (!el) return;
  try {
    const items = await DashboardAPI.generations({ tool, limit: 8 });
    if (!items.length) {
      el.innerHTML = `<p style="color:var(--muted)">${escapeHtml(t("common.no_gens"))}</p>`;
      return;
    }
    el.innerHTML = `
      <h2>${escapeHtml(t("common.recent"))}</h2>
      <div class="gen-cards">
        ${items
          .map(
            (g) => `
          <div class="gen-card">
            <div class="meta"><span>${escapeHtml(g.tool)}</span>${statusBadge(g.status)}</div>
            <strong class="title">${escapeHtml(g.title || "Untitled")}</strong>
            ${
              g.asset_urls?.[0]
                ? `<img class="preview-img" src="${escapeHtml(g.asset_urls[0])}" alt="" style="margin-top:0.5rem;max-height:120px" />`
                : ""
            }
          </div>`
          )
          .join("")}
      </div>`;
  } catch {
    el.innerHTML = "";
  }
}
