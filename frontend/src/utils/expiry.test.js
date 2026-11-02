import { describe, expect, it } from 'vitest'
import { daysUntil, expiryStatus } from './expiry'

const today = new Date(2026, 10, 2) // 2 Nov 2026

describe('expiry helpers', () => {
  it('counts days until expiry', () => {
    expect(daysUntil('2026-11-12', today)).toBe(10)
    expect(daysUntil('2026-11-01', today)).toBe(-1)
  })

  it('classifies batches by days left', () => {
    expect(expiryStatus('2026-11-02', today)).toBe('expired')
    expect(expiryStatus('2026-11-20', today)).toBe('critical')
    expect(expiryStatus('2027-01-15', today)).toBe('warning')
    expect(expiryStatus('2027-06-01', today)).toBe('ok')
  })
})
