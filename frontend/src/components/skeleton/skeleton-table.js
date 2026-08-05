/**
 * Skeleton table — row placeholders for list pages.
 */

/**
 * @param {object} [opts]
 * @param {number} [opts.rows]
 * @param {number} [opts.cols]
 * @param {boolean} [opts.withHeader]
 * @param {boolean} [opts.wave]
 * @returns {string}
 */
export function renderTableSkeleton(opts = {}) {
  const rows = Math.max(1, opts.rows ?? 6);
  const cols = Math.max(2, opts.cols ?? 4);
  const wave = opts.wave !== false ? " skeleton-wave" : "";
  const widths = ["w-70", "w-50", "w-40", "w-30", "w-60", "w-20"];

  const header = opts.withHeader !== false
    ? `<tr>${Array.from({ length: cols }, (_, i) =>
        `<td><span class="skeleton-line ${widths[i % widths.length]} sm${wave}"></span></td>`
      ).join("")}</tr>`
    : "";

  const body = Array.from({ length: rows }, () =>
    `<tr>${Array.from({ length: cols }, (_, i) =>
      `<td><span class="skeleton-line ${widths[(i + 1) % widths.length]}${wave}"></span></td>`
    ).join("")}</tr>`
  ).join("");

  return `
    <div class="skeleton-panel skeleton-base" style="padding:0.5rem 1rem">
      <table class="skeleton-table" role="presentation" aria-hidden="true">
        <tbody>${header}${body}</tbody>
      </table>
    </div>
  `;
}

/**
 * List page: title + filter chips + table.
 * @param {object} [opts]
 * @param {number} [opts.rows]
 * @param {number} [opts.filters]
 * @returns {string}
 */
export function renderListPageSkeleton(opts = {}) {
  const filters = Math.max(1, opts.filters ?? 3);
  const filterHtml = Array.from({ length: filters }, () =>
    `<span class="skeleton-btn skeleton-wave" style="width:5.5rem;height:2rem"></span>`
  ).join("");

  return `
    <div class="skeleton-base" aria-busy="true" aria-live="polite">
      <span class="skeleton-line lg w-40 skeleton-wave"></span>
      <div class="skeleton-row" style="margin:1rem 0;flex-wrap:wrap;gap:0.5rem">
        ${filterHtml}
      </div>
      ${renderTableSkeleton({ rows: opts.rows ?? 8, cols: opts.cols ?? 4 })}
    </div>
  `;
}
