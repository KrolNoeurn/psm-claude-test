import { beforeEach, describe, expect, it } from 'vitest'
import { enqueueSale, queuedSales, syncQueue } from './offline'

describe('offline sale queue', () => {
  beforeEach(() => localStorage.clear())

  it('sends queued sales and keeps them when the network is down', async () => {
    enqueueSale({ client_uuid: 'a' })
    enqueueSale({ client_uuid: 'b' })
    const offline = await syncQueue(async () => { throw new Error('Network Error') })
    expect(offline).toEqual({ sent: 0, failed: 0, remaining: 2 })

    const sent = []
    const online = await syncQueue(async (p) => { sent.push(p.client_uuid) })
    expect(sent).toEqual(['a', 'b'])
    expect(queuedSales()).toHaveLength(0)
    expect(online.sent).toBe(2)
  })

  it('marks a sale the server rejects and continues', async () => {
    enqueueSale({ client_uuid: 'bad' })
    enqueueSale({ client_uuid: 'good' })
    const result = await syncQueue(async (p) => {
      if (p.client_uuid === 'bad') {
        const e = new Error('400')
        e.response = { status: 400, data: { detail: 'Not enough stock' } }
        throw e
      }
    })
    expect(result).toEqual({ sent: 1, failed: 1, remaining: 1 })
    expect(queuedSales()[0].error).toBe('Not enough stock')
  })
})
