/**
 * Skeleton card grid — reusable card placeholders.
 */

/**
 * @param {object} [opts]
 * @param {number} [opts.count]
 * @param {number} [opts.height]
 * @param {boolean} [opts.wave]
 * @returns {string}
 */
export function renderCardSkeleton(opts = {}) {
  const count = Math.max(1, opts.count ?? 4);
  const height = opts.height ?? 80;
  const wave = opts.wave ? " skeleton-wave" : "";
  const cards = Array.from({ length: count }, () => `
    <div class="skeleton-panel skeleton-base" style="margin:0">
      <div class="skeleton-box${wave}" style="height:${height}px;min-height:${height}px"></div>
      <span class="skeleton-line w-70${wave}"></span>
      <span class="skeleton-line w-40 sm${wave}"></span>
    </div>
  `).join("");
  return `<div class="skeleton-grid skeleton-base">${cards}</div>`;
}

/**
 * Compact metric cards (stat strip).
 * @param {object} [opts]
 * @param {number} [opts.count]
 * @returns {string}
 */
export function renderStatCardsSkeleton(opts = {}) {
  const count = Math.max(1, opts.count ?? 4);
  const cards = Array.from({ length: count }, () => `
    <div class="stat skeleton-base" style="min-height:80px">
      <span class="skeleton-line w-50 sm skeleton-wave"></span>
      <span class="skeleton-line w-40 lg skeleton-wave" style="margin-top:0.75rem"></span>
    </div>
  `).join("");
  return `<div class="stats skeleton-base">${cards}</div>`;
}
