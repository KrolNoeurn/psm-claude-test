const DAY = 24 * 60 * 60 * 1000

/** Whole days from `today` until an ISO expiry date (negative = expired). */
export function daysUntil(expiryIso, today = new Date()) {
  const [y, m, d] = expiryIso.split('-').map(Number)
  const expiry = Date.UTC(y, m - 1, d)
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((expiry - start) / DAY)
}

/** Status used to colour a batch row: expired, critical (≤30 d), warning (≤90 d) or ok. */
export function expiryStatus(expiryIso, today = new Date()) {
  const days = daysUntil(expiryIso, today)
  if (days <= 0) return 'expired'
  if (days <= 30) return 'critical'
  if (days <= 90) return 'warning'
  return 'ok'
}
