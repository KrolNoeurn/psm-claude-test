// Helpers for purchase orders and goods receipts.
// Quantities are typed in a unit (box, strip, tablet); stock is in base units.

export function toBase(qty, factor) {
  return (Number(qty) || 0) * (Number(factor) || 0)
}

export function lineTotal(qty, price) {
  return (Number(qty) || 0) * (Number(price) || 0)
}

export function money(value) {
  return Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// Show base units as "2 Box + 3 Strip + 5 Tablet" using the product's units.
export function describeBase(baseQty, units) {
  let rest = Number(baseQty) || 0
  if (!units?.length) return String(rest)
  const parts = []
  for (const u of [...units].sort((a, b) => b.factor - a.factor)) {
    const n = Math.floor(rest / u.factor)
    if (n > 0) {
      parts.push(`${n} ${u.unit_name}`)
      rest -= n * u.factor
    }
  }
  return parts.length ? parts.join(' + ') : `0 ${units.find((u) => u.is_base)?.unit_name || ''}`.trim()
}

// Pick the unit and quantity to prefill a receipt row from what is still on order:
// the ordered unit when the remainder is whole, otherwise the base unit.
export function suggestReceipt(remainingBase, orderedUnit, units) {
  if (orderedUnit && remainingBase % orderedUnit.factor === 0) {
    return { unitId: orderedUnit.id, factor: orderedUnit.factor, qty: remainingBase / orderedUnit.factor }
  }
  const base = units.find((u) => u.is_base) || { id: orderedUnit?.id, factor: 1 }
  return { unitId: base.id, factor: base.factor, qty: remainingBase }
}

// Cost per unit converted between units, e.g. box price 12.00 -> strip price 1.20.
export function convertCost(cost, fromFactor, toFactor) {
  if (!fromFactor) return Number(cost) || 0
  return Math.round(((Number(cost) || 0) / fromFactor) * toFactor * 10000) / 10000
}

// Check receipt rows before posting. Returns a list of { row, key } errors
// where `key` is an i18n key under `purchasing.errors`.
export function validateReceiptRows(rows, today = new Date()) {
  const errors = []
  const todayStr = isoDate(today)
  const perOrderLine = {}
  rows.forEach((r, i) => {
    if (!r.product_unit) errors.push({ row: i, key: 'unit' })
    if (!(Number(r.qty) > 0)) errors.push({ row: i, key: 'qty' })
    if (!String(r.batch_no || '').trim()) errors.push({ row: i, key: 'batch' })
    if (!r.expiry_date) errors.push({ row: i, key: 'expiryMissing' })
    else if (r.expiry_date <= todayStr) errors.push({ row: i, key: 'expired' })
    if (r.order_line) {
      perOrderLine[r.order_line] = (perOrderLine[r.order_line] || 0) + toBase(r.qty, r.factor)
      if (perOrderLine[r.order_line] > r.remaining_base_qty) errors.push({ row: i, key: 'tooMany' })
    }
  })
  return errors
}

export function isoDate(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// Turn a DRF error response into one readable line.
export function apiError(err) {
  const data = err?.response?.data
  if (!data) return err?.message || 'Error'
  if (typeof data === 'string') return data
  const flat = []
  const walk = (v, path) => {
    if (Array.isArray(v)) v.forEach((x, i) => walk(x, typeof x === 'object' ? `${path}[${i + 1}]` : path))
    else if (v && typeof v === 'object') Object.entries(v).forEach(([k, x]) => walk(x, k === 'detail' || k === 'non_field_errors' ? path : `${path ? path + '.' : ''}${k}`))
    else flat.push(path ? `${path}: ${v}` : String(v))
  }
  walk(data, '')
  return flat.join(' · ')
}
