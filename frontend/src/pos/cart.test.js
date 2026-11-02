import { describe, expect, it } from 'vitest'
import { cartTotals, changeDue, findByBarcode, priceFor, searchCatalog, toRiel } from './cart'

const strip = { id: 2, factor: 10, barcode: 'PARAS', prices: [{ min_qty: 1, price: '2.50' }, { min_qty: 5, price: '2.20' }] }
const tab = { id: 1, factor: 1, barcode: 'PARAT', prices: [{ min_qty: 1, price: '0.30' }] }
const catalog = [{ id: 9, sku: 'PARA', name: 'Panadol 500 mg', generic_name: 'Paracetamol', units: [tab, strip] }]

describe('pos cart', () => {
  it('uses the highest quantity break reached', () => {
    expect(priceFor(strip, 1)).toBe(250)
    expect(priceFor(strip, 5)).toBe(220)
    expect(priceFor({ prices: [] }, 1)).toBeNull()
  })

  it('totals lines, discount and optional VAT in cents', () => {
    const lines = [{ unit: strip, qty: 2, discount: 0 }, { unit: tab, qty: 3, discount: '0.10' }]
    expect(cartTotals(lines, '0.30')).toEqual({ subtotal: 580, discount: 30, vat: 0, total: 550 })
    expect(cartTotals(lines, 0, { enabled: true, rate: '10' }).total).toBe(638)
  })

  it('rounds riel to 100 and computes change', () => {
    expect(toRiel(250, 4100)).toBe(10300)
    const due = changeDue(250, [{ method: 'cash_khr', amount: 20000 }], 4100)
    expect(due.enough).toBe(true)
    expect(due.changeRiel).toBe(9700)
    expect(changeDue(250, [{ method: 'cash_usd', amount: 1 }], 4100).enough).toBe(false)
  })

  it('finds by barcode and searches by name', () => {
    expect(findByBarcode(catalog, 'PARAS').unit.id).toBe(2)
    expect(findByBarcode(catalog, 'nope')).toBeNull()
    expect(searchCatalog(catalog, 'parac')).toHaveLength(1)
  })
})
