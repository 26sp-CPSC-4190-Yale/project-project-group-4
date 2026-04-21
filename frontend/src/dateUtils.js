export function parseYear(dateStr) {
  if (!dateStr) return null
  const match = dateStr.match(/\b(\d{3,4})\b/)
  return match ? parseInt(match[1], 10) : null
}

export function centuryFromYear(year) {
  if (year == null) return null
  return Math.ceil(year / 100)
}

function ordinalSuffix(n) {
  const v = n % 100
  if (v >= 11 && v <= 13) return 'th'
  switch (n % 10) {
    case 1: return 'st'
    case 2: return 'nd'
    case 3: return 'rd'
    default: return 'th'
  }
}

export function eraLabel(century) {
  if (century == null) return 'Unknown era'
  return `${century}${ordinalSuffix(century)} century`
}

export function buildEraBreakdown(artworks) {
  const counts = new Map()
  for (const a of artworks) {
    const century = centuryFromYear(parseYear(a.date))
    const label = eraLabel(century)
    counts.set(label, (counts.get(label) || 0) + 1)
  }
  const total = artworks.length || 1
  return [...counts.entries()]
    .map(([label, count]) => ({
      label,
      count,
      percent: Math.round((count / total) * 100),
    }))
    .sort((a, b) => {
      if (a.label === 'Unknown era') return 1
      if (b.label === 'Unknown era') return -1
      return b.count - a.count
    })
}
