// Pure cart maths for the POS. Money is kept in integer cents to avoid
// floating point errors; the server recomputes everything on checkout.

export const toCents = (value) => Math.round(Number(value || 0) * 100)
export const fromCents = (cents) => (cents / 100).toFixed(2)

/** Retail price (cents) of a unit for a quantity: the highest quantity break reached. */
export function priceFor(unit, qty) {
  let best = null
  for (const p of unit.prices || []) {
    if (p.min_qty <= qty && (!best || p.min_qty > best.min_qty)) best = p
  }
  return best ? toCents(best.price) : null
}

export function lineTotal(line) {
  const price = priceFor(line.unit, line.qty) ?? 0
  return Math.max(price * line.qty - toCents(line.discount), 0)
}

/** Totals in cents. `vat` is { enabled, rate } from shop settings. */
export function cartTotals(lines, discount = 0, vat = { enabled: false, rate: 0 }) {
  const subtotal = lines.reduce((sum, l) => sum + lineTotal(l), 0)
  const disc = Math.min(toCents(discount), subtotal)
  const taxable = subtotal - disc
  const vatAmount = vat.enabled ? Math.round((taxable * Number(vat.rate)) / 100) : 0
  return { subtotal, discount: disc, vat: vatAmount, total: taxable + vatAmount }
}

/** Riel amount for dollars, in 100-riel steps (half rounds up). */
export function toRiel(cents, rate) {
  const riel = (cents / 100) * Number(rate)
  return Math.round(riel / 100) * 100
}

/** Paid amount in cents from payment rows ({method, amount}). */
export function paidCents(payments, rate) {
  return payments.reduce((sum, p) => {
    const amount = Number(p.amount || 0)
    return sum + (p.method === 'cash_khr' ? Math.round((amount / Number(rate)) * 100) : toCents(amount))
  }, 0)
}

/** Change to give back in dollars (cents) and in riel. Riel change is worked
 * out from riel amounts so a riel payment gets exact riel change. */
export function changeDue(totalCents, payments, rate) {
  const paid = paidCents(payments, rate)
  const change = Math.max(paid - totalCents, 0)
  const paidRiel = payments.reduce(
    (sum, p) => sum + (p.method === 'cash_khr' ? Number(p.amount || 0) : Number(p.amount || 0) * Number(rate)),
    0,
  )
  const changeRiel = Math.max(Math.floor((paidRiel - toRiel(totalCents, rate)) / 100) * 100, 0)
  // 100 riel of rounding is accepted as fully paid, like the server.
  const tolerance = Math.round((100 / Number(rate)) * 100)
  return { paid, change, changeRiel, enough: paid + tolerance >= totalCents }
}

/** Find a product unit by its barcode (exact) in the cached catalog. */
export function findByBarcode(catalog, code) {
  const wanted = String(code).trim()
  if (!wanted) return null
  for (const product of catalog) {
    const unit = product.units.find((u) => u.barcode && u.barcode === wanted)
    if (unit) return { product, unit }
  }
  return null
}

/** Simple search on name, generic name, SKU or barcode. */
export function searchCatalog(catalog, text, limit = 20) {
  const q = text.trim().toLowerCase()
  if (!q) return []
  const out = []
  for (const p of catalog) {
    const hay = [p.name, p.generic_name, p.brand_name, p.sku, ...p.units.map((u) => u.barcode)]
      .filter(Boolean).join(' ').toLowerCase()
    if (hay.includes(q)) out.push(p)
    if (out.length >= limit) break
  }
  return out
}

/** Base units already in the cart for a product (to warn before overselling). */
export function baseQtyInCart(lines, productId) {
  return lines.filter((l) => l.product.id === productId).reduce((s, l) => s + l.qty * l.unit.factor, 0)
}
