/**
 * Skeleton for detail / entity pages.
 */
import { renderStatCardsSkeleton } from "./skeleton-card.js";
import { renderTableSkeleton } from "./skeleton-table.js";

/**
 * @param {object} [opts]
 * @param {number} [opts.metrics]
 * @param {number} [opts.rows]
 * @param {number} [opts.chartHeight]
 * @returns {string}
 */
export function renderDetailSkeleton(opts = {}) {
  const metrics = opts.metrics ?? 3;
  const chartH = opts.chartHeight ?? 200;
  return `
    <div class="skeleton-base" aria-busy="true" aria-live="polite">
      <div class="skeleton-row" style="margin-bottom:1.25rem">
        <span class="skeleton-circle lg skeleton-wave"></span>
        <div class="skeleton-col">
          <span class="skeleton-line lg w-50 skeleton-wave"></span>
          <span class="skeleton-line w-40 sm skeleton-wave"></span>
        </div>
        <span class="skeleton-btn skeleton-wave" style="margin-left:auto"></span>
      </div>

      ${renderStatCardsSkeleton({ count: metrics })}

      <div class="skeleton-panel" style="margin-top:1rem">
        <span class="skeleton-line w-30 skeleton-wave"></span>
        <div class="skeleton-box skeleton-wave" style="height:${chartH}px;min-height:${chartH}px;margin-top:0.75rem"></div>
      </div>

      <div style="margin-top:0.5rem">
        <span class="skeleton-line w-40 skeleton-wave"></span>
        ${renderTableSkeleton({ rows: opts.rows ?? 4, cols: 3 })}
      </div>
    </div>
  `;
}
