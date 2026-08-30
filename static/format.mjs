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

/** Display names for reference slugs — mirrors REFERENCE_NAMES in pdf_utils.py. */
const REFERENCE_NAMES = {
  'uk-who': 'UK-WHO',
  'turners-syndrome': 'Turner Syndrome',
  'trisomy-21': 'Trisomy 21',
  'cdc': 'CDC (US)',
  'who': 'WHO',
  'trisomy-21-aap': 'Trisomy 21 (AAP, US)',
};

/** Human-readable name for a growth reference slug; unknown slugs are upper-cased. */
export function formatReferenceName(slug) {
  const key = slug || 'uk-who';
  return REFERENCE_NAMES[key] || key.toUpperCase();
}
