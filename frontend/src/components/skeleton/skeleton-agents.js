/**
 * Skeleton for agents / tool list pages.
 */
import { renderCardSkeleton } from "./skeleton-card.js";
import { renderListPageSkeleton } from "./skeleton-table.js";

/**
 * Card-grid agents catalog skeleton.
 * @param {object} [opts]
 * @param {number} [opts.cards]
 * @returns {string}
 */
export function renderAgentsSkeleton(opts = {}) {
  return `
    <div class="skeleton-base" aria-busy="true" aria-live="polite">
      <span class="skeleton-line lg w-40 skeleton-wave"></span>
      <span class="skeleton-line w-60 sm skeleton-wave" style="margin-bottom:1rem"></span>
      <div class="skeleton-row" style="margin-bottom:1rem;flex-wrap:wrap;gap:0.5rem">
        <span class="skeleton-btn skeleton-wave" style="width:6rem"></span>
        <span class="skeleton-btn skeleton-wave" style="width:5rem"></span>
        <span class="skeleton-btn skeleton-wave" style="width:7rem"></span>
      </div>
      ${renderCardSkeleton({ count: opts.cards ?? 6, height: 120 })}
    </div>
  `;
}

/**
 * Table-style agents / users list.
 * @param {object} [opts]
 * @returns {string}
 */
export function renderAgentsTableSkeleton(opts = {}) {
  return renderListPageSkeleton({
    rows: opts.rows ?? 8,
    filters: opts.filters ?? 3,
    cols: opts.cols ?? 4,
  });
}
