'use strict';

// Formats century value to be readable
export function formatCentury(value) {
  const n = parseInt(value, 10);
  if (Number.isNaN(n)) return value;
  const abs = Math.abs(n);
  const suffix = abs % 10 === 1 && abs !== 11 ? 'st'
    : abs % 10 === 2 && abs !== 12 ? 'nd'
    : abs % 10 === 3 && abs !== 13 ? 'rd' : 'th';
  return `${abs}${suffix} century${n < 0 ? ' BC' : ''}`;
}

// To have the option to format other facets when needed
export function formatFacetValue(facet, value) {
  return facet === 'century' ? formatCentury(value) : value;
}
