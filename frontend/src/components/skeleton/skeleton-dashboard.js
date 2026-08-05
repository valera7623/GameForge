/**
 * Skeleton for dashboard layout.
 */
import { renderStatCardsSkeleton } from "./skeleton-card.js";
import { renderTableSkeleton } from "./skeleton-table.js";

/**
 * @param {object} [opts]
 * @param {boolean} [opts.compact]
 * @returns {string}
 */
export function renderDashboardSkeleton(opts = {}) {
  const chartH = opts.compact ? 200 : 300;
  return `
    <div class="skeleton-base" aria-busy="true" aria-live="polite">
      <div class="skeleton-row" style="margin-bottom:1.25rem">
        <span class="skeleton-circle lg skeleton-wave"></span>
        <div class="skeleton-col">
          <span class="skeleton-line lg w-50 skeleton-wave"></span>
          <span class="skeleton-line w-30 sm skeleton-wave"></span>
        </div>
      </div>

      ${renderStatCardsSkeleton({ count: 4 })}

      <div class="skeleton-panel" style="margin-top:1rem">
        <span class="skeleton-line w-30 skeleton-wave"></span>
        <div class="skeleton-box skeleton-wave" style="height:${chartH}px;min-height:${chartH}px;margin-top:0.75rem"></div>
      </div>

      <div style="margin-top:0.5rem">
        <span class="skeleton-line w-40 skeleton-wave"></span>
        ${renderTableSkeleton({ rows: 5, cols: 3, withHeader: true })}
      </div>
    </div>
  `;
}
