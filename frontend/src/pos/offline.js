// Keeps the POS selling when the internet drops: the catalog is cached in the
// browser and finished sales wait in a queue until the server is reachable.
// Each sale carries a client_uuid, so sending it twice never creates two sales.

const CATALOG_KEY = 'pos-catalog-v1'
const QUEUE_KEY = 'pos-queue-v1'

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

export const loadCatalog = () => read(CATALOG_KEY, null)
export const saveCatalog = (catalog) => write(CATALOG_KEY, catalog)

export const queuedSales = () => read(QUEUE_KEY, [])
export function enqueueSale(payload) {
  const queue = queuedSales()
  queue.push({ payload, queuedAt: new Date().toISOString(), error: null })
  write(QUEUE_KEY, queue)
}
function saveQueue(queue) {
  write(QUEUE_KEY, queue)
}

/** True when the request never reached the server (offline, DNS, timeout). */
export function isNetworkError(error) {
  return !error.response
}

/**
 * Send queued sales in order. Network errors stop the run (try later);
 * a sale the server rejects stays in the queue marked with the reason so
 * a manager can see it. Returns { sent, failed, remaining }.
 */
export async function syncQueue(post) {
  const queue = queuedSales()
  let sent = 0
  let failed = 0
  const keep = []
  for (let i = 0; i < queue.length; i++) {
    const entry = queue[i]
    if (entry.error) {
      keep.push(entry)
      failed++
      continue
    }
    try {
      await post(entry.payload)
      sent++
    } catch (error) {
      if (isNetworkError(error)) {
        keep.push(...queue.slice(i))
        break
      }
      entry.error = error.response?.data?.detail || `HTTP ${error.response.status}`
      keep.push(entry)
      failed++
    }
  }
  saveQueue(keep)
  return { sent, failed, remaining: keep.length }
}

export function dropQueued(clientUuid) {
  saveQueue(queuedSales().filter((e) => e.payload.client_uuid !== clientUuid))
}

export function newUuid() {
  if (crypto?.randomUUID) return crypto.randomUUID()
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}
