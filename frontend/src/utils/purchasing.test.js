import { describe, expect, it } from 'vitest'
import { apiError, convertCost, describeBase, suggestReceipt, toBase, validateReceiptRows } from './purchasing'

const units = [
  { id: 1, unit_name: 'Tablet', factor: 1, is_base: true },
  { id: 2, unit_name: 'Strip', factor: 10, is_base: false },
  { id: 3, unit_name: 'Box', factor: 100, is_base: false },
]
const today = new Date(2026, 10, 2)

describe('purchasing helpers', () => {
  it('converts to base units', () => {
    expect(toBase(3, 100)).toBe(300)
    expect(toBase('', 10)).toBe(0)
  })

  it('describes base units with the biggest units first', () => {
    expect(describeBase(235, units)).toBe('2 Box + 3 Strip + 5 Tablet')
    expect(describeBase(0, units)).toBe('0 Tablet')
  })

  it('suggests the ordered unit when the remainder is whole', () => {
    expect(suggestReceipt(300, units[2], units)).toEqual({ unitId: 3, factor: 100, qty: 3 })
    expect(suggestReceipt(250, units[2], units)).toEqual({ unitId: 1, factor: 1, qty: 250 })
  })

  it('converts cost between units', () => {
    expect(convertCost('12.00', 100, 10)).toBe(1.2)
  })

  it('validates receipt rows', () => {
    const row = { product_unit: 3, factor: 100, qty: 2, batch_no: 'L1', expiry_date: '2028-01-01', order_line: 9, remaining_base_qty: 300 }
    expect(validateReceiptRows([row], today)).toEqual([])
    const bad = [{ ...row, expiry_date: '2026-11-02' }, { ...row, batch_no: ' ' }]
    expect(validateReceiptRows(bad, today).map((e) => e.key)).toEqual(['expired', 'batch', 'tooMany'])
  })

  it('flattens API errors', () => {
    expect(apiError({ response: { data: { detail: 'Nope' } } })).toBe('Nope')
    expect(apiError({ response: { data: { lines: [{ qty: ['Too small'] }] } } })).toBe('lines[1].qty: Too small')
  })
})
