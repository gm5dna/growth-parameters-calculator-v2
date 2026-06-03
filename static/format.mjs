/**
 * Shared clinical value formatting.
 *
 * Single source of truth for how centiles and SDS are rendered so the on-screen
 * cards, the clipboard export, and the chart tooltips can never drift apart.
 */

/** Format a centile as "46.4%". Null/undefined -> "N/A". */
export function formatCentile(centile) {
  if (centile === null || centile === undefined) return 'N/A';
  return centile.toFixed(1) + '%';
}

/** Format an SDS with an explicit sign, e.g. "+0.16" / "-0.39". Null/undefined -> "N/A". */
export function formatSds(sds) {
  if (sds === null || sds === undefined) return 'N/A';
  const sign = sds >= 0 ? '+' : '';
  return sign + sds.toFixed(2);
}
