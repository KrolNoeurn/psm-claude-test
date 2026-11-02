<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '../api/http'
import PosReceipt from '../components/PosReceipt.vue'
import {
  baseQtyInCart, cartTotals, changeDue, findByBarcode, fromCents, lineTotal, priceFor,
  searchCatalog, toCents, toRiel,
} from '../pos/cart'
import {
  dropQueued, enqueueSale, isNetworkError, loadCatalog, newUuid, queuedSales, saveCatalog, syncQueue,
} from '../pos/offline'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

// ---- catalog (cached for offline use) ----
const catalog = ref(loadCatalog())
const products = computed(() => catalog.value?.products || [])
const rate = computed(() => Number(catalog.value?.exchange_rate || 4000))
const settings = computed(() => catalog.value?.settings || { receipt_width: '80', vat_enabled: false, vat_rate: 0 })
const online = ref(navigator.onLine)
const loadError = ref('')

async function refreshCatalog() {
  try {
    const { data } = await http.get('/pos/catalog/')
    catalog.value = data
    saveCatalog(data)
    loadError.value = ''
  } catch (error) {
    if (error.response?.status === 400) loadError.value = t('pos.noBranch')
    else if (isNetworkError(error)) online.value = false
  }
}

// ---- scan / search ----
const code = ref('')
const message = ref('')
const scanInput = ref(null)
const results = computed(() => (code.value.length >= 2 ? searchCatalog(products.value, code.value, 8) : []))

function focusScan() {
  nextTick(() => scanInput.value?.focus())
}

function onScanEnter() {
  const hit = findByBarcode(products.value, code.value)
  if (hit) {
    addToCart(hit.product, hit.unit)
  } else if (results.value.length === 1) {
    pickProduct(results.value[0])
  } else if (!results.value.length) {
    message.value = t('pos.noMatch', { code: code.value })
  }
}

function pickProduct(product) {
  // Default to the smallest unit that has a price.
  const unit = [...product.units].sort((a, b) => a.factor - b.factor).find((u) => u.prices.length) || product.units[0]
  addToCart(product, unit)
}

// ---- cart ----
const lines = ref([])
const saleDiscount = ref('')

function addToCart(product, unit) {
  message.value = ''
  const existing = lines.value.find((l) => l.unit.id === unit.id)
  if (existing) existing.qty += 1
  else lines.value.push({ key: newUuid(), product, unit, qty: 1, discount: '' })
  checkStock(product)
  code.value = ''
  focusScan()
}

function checkStock(product) {
  const want = baseQtyInCart(lines.value, product.id)
  if (want > product.stock) message.value = `${product.name}: ${t('pos.outOfStock', { n: product.stock })}`
}

function changeUnit(line, unitId) {
  line.unit = line.product.units.find((u) => u.id === Number(unitId))
  checkStock(line.product)
}

function removeLine(line) {
  lines.value = lines.value.filter((l) => l !== line)
}

const totals = computed(() =>
  cartTotals(lines.value, saleDiscount.value, { enabled: settings.value.vat_enabled, rate: settings.value.vat_rate }),
)
const hasControlled = computed(() => lines.value.some((l) => l.product.is_controlled))
const missingPrice = computed(() => lines.value.some((l) => priceFor(l.unit, l.qty) === null))

function newSale() {
  lines.value = []
  saleDiscount.value = ''
  message.value = ''
  focusScan()
}

// ---- payment ----
const paying = ref(false)
const pay = reactive({ rows: [], customer: '', phone: '', approver: '', approverPassword: '', rx: null })
const busy = ref(false)
const payError = ref('')
const due = computed(() => changeDue(totals.value.total, pay.rows, rate.value))

function openPayment() {
  if (!lines.value.length || missingPrice.value) return
  pay.rows = [{ method: 'cash_usd', amount: fromCents(totals.value.total), reference: '' }]
  pay.customer = ''
  pay.phone = ''
  pay.approver = ''
  pay.approverPassword = ''
  pay.rx = null
  payError.value = ''
  paying.value = true
}

function setMethod(row, method) {
  row.method = method
  row.amount = method === 'cash_khr' ? toRiel(totals.value.total, rate.value) : fromCents(totals.value.total)
}

function addPaymentRow() {
  pay.rows.push({ method: 'cash_khr', amount: '', reference: '' })
}

function buildPayload() {
  return {
    client_uuid: newUuid(),
    sold_at: new Date().toISOString(),
    lines: lines.value.map((l) => ({ product_unit: l.unit.id, qty: l.qty, discount: l.discount || 0 })),
    payments: pay.rows.filter((r) => Number(r.amount) > 0).map((r) => ({
      method: r.method, amount: String(r.amount), reference: r.reference || '',
    })),
    discount: saleDiscount.value || 0,
    customer_name: pay.customer,
    customer_phone: pay.phone,
    approver_username: pay.approver,
    approver_password: pay.approverPassword,
  }
}

function postSale(payload, rx) {
  if (!rx) return http.post('/sales/', payload)
  // With a prescription photo the sale goes as multipart: the photo plus the sale as JSON.
  const form = new FormData()
  form.append('prescription_image', rx)
  form.append('data', JSON.stringify(payload))
  return http.post('/sales/', form)
}

// Receipt shown after a sale (server answer, or a local copy when offline).
const lastSale = ref(null)

function localReceipt(payload) {
  const items = lines.value.map((l) => ({
    product_name: l.product.name, unit_name: l.unit.unit, unit_name_km: l.unit.unit_km, qty: l.qty,
    unit_price: fromCents(priceFor(l.unit, l.qty)), discount: fromCents(toCents(l.discount)), line_total: fromCents(lineTotal(l)),
  }))
  return {
    number: payload.client_uuid.slice(0, 8).toUpperCase(), offline: true, sold_at: payload.sold_at,
    cashier_name: auth.user?.username || '', customer_name: payload.customer_name, items,
    subtotal: fromCents(totals.value.subtotal), discount: fromCents(totals.value.discount),
    vat_rate: settings.value.vat_rate, vat_amount: fromCents(totals.value.vat), total: fromCents(totals.value.total),
    total_khr: toRiel(totals.value.total, rate.value), payments: payload.payments.map((p) => ({ ...p, currency: p.method === 'cash_khr' ? 'KHR' : 'USD' })),
    change_usd: fromCents(due.value.change), exchange_rate: rate.value,
  }
}

async function completeSale() {
  if (!due.value.enough || busy.value) return
  busy.value = true
  payError.value = ''
  const payload = buildPayload()
  const changeRiel = due.value.changeRiel
  try {
    const { data } = await postSale(payload, pay.rx)
    lastSale.value = { ...data, change_riel: changeRiel }
    online.value = true
    finishSale(t('pos.done', { number: data.number }))
    refreshCatalog()
  } catch (error) {
    if (isNetworkError(error)) {
      if (hasControlled.value && !catalog.value?.can_approve) {
        payError.value = t('pos.controlledOffline')
      } else {
        // Never keep a pharmacist password on the device.
        enqueueSale({ ...payload, approver_username: '', approver_password: '' })
        online.value = false
        lastSale.value = { ...localReceipt(payload), change_riel: changeRiel }
        finishSale(t('pos.savedOffline'))
        refreshQueue()
      }
    } else {
      payError.value = error.response?.data?.detail
        || Object.values(error.response?.data || {}).flat().join(' ')
        || `HTTP ${error.response?.status}`
    }
  } finally {
    busy.value = false
  }
}

function finishSale(msg) {
  paying.value = false
  newSale()
  message.value = msg
}

function printReceipt() {
  window.print()
}

// ---- offline queue ----
const queue = ref(queuedSales())
const failedQueue = computed(() => queue.value.filter((e) => e.error))
const syncing = ref(false)

function refreshQueue() {
  queue.value = queuedSales()
}

async function syncNow() {
  if (syncing.value || !queue.value.length) return
  syncing.value = true
  try {
    const result = await syncQueue((payload) => http.post('/sales/', payload))
    if (result.sent) {
      online.value = true
      refreshCatalog()
    }
  } finally {
    syncing.value = false
    refreshQueue()
  }
}

function discardFailed(entry) {
  dropQueued(entry.payload.client_uuid)
  refreshQueue()
}

function goOnline() {
  online.value = true
  syncNow()
}
function goOffline() {
  online.value = false
}

let timer
onMounted(async () => {
  window.addEventListener('online', goOnline)
  window.addEventListener('offline', goOffline)
  timer = setInterval(syncNow, 30000)
  focusScan()
  await refreshCatalog()
  syncNow()
})
onBeforeUnmount(() => {
  window.removeEventListener('online', goOnline)
  window.removeEventListener('offline', goOffline)
  clearInterval(timer)
})

const catalogTime = computed(() =>
  catalog.value?.generated_at ? new Date(catalog.value.generated_at).toLocaleTimeString() : '–',
)
const money = (cents) => '$' + fromCents(cents)
const riel = (n) => Number(n).toLocaleString('en-US') + ' ៛'
</script>

<template>
  <div class="pos no-print">
    <div class="pos-bar">
      <span class="pill" :class="online ? 'ok' : 'off'">{{ online ? t('pos.online') : t('pos.offline') }}</span>
      <span class="muted">{{ t('pos.rate', { rate: rate.toLocaleString('en-US') }) }}</span>
      <span class="muted">{{ t('pos.catalogAge', { time: catalogTime }) }}</span>
      <button class="link" type="button" @click="refreshCatalog">{{ t('pos.refresh') }}</button>
      <span class="spacer" />
      <template v-if="queue.length">
        <span class="pill warn">{{ t('pos.pending', { n: queue.length }) }}</span>
        <button class="link" type="button" :disabled="syncing" @click="syncNow">{{ t('pos.syncNow') }}</button>
      </template>
    </div>

    <p v-if="loadError" class="error">{{ loadError }}</p>
    <div v-for="entry in failedQueue" :key="entry.payload.client_uuid" class="error row-between">
      <span>{{ t('pos.failedSync', { n: 1, reason: entry.error }) }} ({{ new Date(entry.queuedAt).toLocaleString() }})</span>
      <button class="link" type="button" @click="discardFailed(entry)">{{ t('common.remove') }}</button>
    </div>

    <div class="pos-grid">
      <section class="left">
        <div class="scan">
          <input
            id="pos-scan" ref="scanInput" v-model="code" class="scan-input" :placeholder="t('pos.scan')"
            autocomplete="off" @keydown.enter.prevent="onScanEnter"
          />
          <ul v-if="results.length" class="results">
            <li v-for="p in results" :key="p.id">
              <button type="button" @click="pickProduct(p)">
                <span>{{ p.name }} <small class="muted">{{ p.generic_name }}</small></span>
                <span class="muted">{{ p.stock }}</span>
              </button>
            </li>
          </ul>
        </div>
        <p v-if="message" class="message">{{ message }}</p>

        <table class="grid cart">
          <thead>
            <tr>
              <th>{{ t('products.name') }}</th><th>{{ t('pos.unit') }}</th><th class="num">{{ t('pos.qty') }}</th>
              <th class="num">{{ t('pos.price') }}</th><th class="num">{{ t('pos.lineDiscount') }}</th><th class="num">{{ t('pos.amount') }}</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in lines" :key="line.key">
              <td>
                {{ line.product.name }}
                <span v-if="line.product.is_controlled" class="pill warn">Rx!</span>
                <span v-else-if="line.product.is_prescription_required" class="pill">Rx</span>
              </td>
              <td>
                <select :id="`unit-${line.key}`" :value="line.unit.id" @change="changeUnit(line, $event.target.value)">
                  <option v-for="u in line.product.units" :key="u.id" :value="u.id">{{ u.unit_km || u.unit }} (×{{ u.factor }})</option>
                </select>
              </td>
              <td class="num">
                <div class="qty">
                  <button type="button" :disabled="line.qty <= 1" @click="line.qty--">−</button>
                  <input :id="`qty-${line.key}`" v-model.number="line.qty" type="number" min="1" @change="checkStock(line.product)" />
                  <button type="button" @click="line.qty++; checkStock(line.product)">+</button>
                </div>
              </td>
              <td class="num">{{ priceFor(line.unit, line.qty) === null ? '—' : money(priceFor(line.unit, line.qty)) }}</td>
              <td class="num"><input :id="`disc-${line.key}`" v-model="line.discount" class="small-input" type="number" min="0" step="0.01" placeholder="0" /></td>
              <td class="num">{{ money(lineTotal(line)) }}</td>
              <td><button class="link" type="button" @click="removeLine(line)">✕</button></td>
            </tr>
            <tr v-if="!lines.length"><td colspan="7" class="muted center">{{ t('pos.emptyCart') }}</td></tr>
          </tbody>
        </table>
      </section>

      <aside class="right">
        <div class="sum-row"><span>{{ t('pos.subtotal') }}</span><span>{{ money(totals.subtotal) }}</span></div>
        <label class="sum-row" for="sale-discount">
          <span>{{ t('pos.discount') }}</span>
          <input id="sale-discount" v-model="saleDiscount" class="small-input" type="number" min="0" step="0.01" placeholder="0.00" />
        </label>
        <div v-if="settings.vat_enabled" class="sum-row"><span>{{ t('pos.vat', { rate: Number(settings.vat_rate) }) }}</span><span>{{ money(totals.vat) }}</span></div>
        <div class="grand">
          <span>{{ t('pos.total') }}</span>
          <strong>{{ money(totals.total) }}</strong>
          <span class="riel">{{ riel(toRiel(totals.total, rate)) }}</span>
        </div>
        <p v-if="hasControlled" class="warn-text">{{ t('pos.controlled') }}</p>
        <button class="primary big" type="button" :disabled="!lines.length || missingPrice" @click="openPayment">{{ t('pos.pay') }}</button>
        <button class="ghost" type="button" :disabled="!lines.length" @click="newSale">{{ t('pos.clear') }}</button>

        <div v-if="lastSale" class="last">
          <span>{{ lastSale.number }} · ${{ lastSale.total }}</span>
          <button class="link" type="button" @click="printReceipt">{{ t('pos.print') }}</button>
        </div>
      </aside>
    </div>

    <div v-if="paying" class="overlay" @keydown.esc="paying = false">
      <form class="dialog" @submit.prevent="completeSale">
        <h3>{{ t('pos.payment') }} — {{ money(totals.total) }} · {{ riel(toRiel(totals.total, rate)) }}</h3>

        <div v-for="(row, i) in pay.rows" :key="i" class="pay-row">
          <div class="methods">
            <button v-for="m in ['cash_usd', 'cash_khr', 'khqr']" :key="m" type="button" :class="{ active: row.method === m }" @click="setMethod(row, m)">{{ t('pos.' + m) }}</button>
          </div>
          <label :for="`pay-amount-${i}`">{{ t('pos.received') }} ({{ row.method === 'cash_khr' ? '៛' : '$' }})
            <input :id="`pay-amount-${i}`" v-model="row.amount" type="number" min="0" :step="row.method === 'cash_khr' ? 100 : 0.01" />
          </label>
          <template v-if="row.method === 'khqr'">
            <p class="muted small">{{ t('pos.khqrHint') }}</p>
            <label :for="`pay-ref-${i}`">{{ t('pos.reference') }}<input :id="`pay-ref-${i}`" v-model="row.reference" type="text" /></label>
          </template>
        </div>
        <button class="link" type="button" @click="addPaymentRow">+ {{ t('pos.addPayment') }}</button>

        <div class="change" :class="{ bad: !due.enough }">
          <template v-if="due.enough">{{ t('pos.change') }}: <strong>{{ money(due.change) }}</strong> · <strong>{{ riel(due.changeRiel) }}</strong></template>
          <template v-else>{{ t('pos.notEnough') }}</template>
        </div>

        <div class="two">
          <label for="pay-customer">{{ t('pos.customer') }}<input id="pay-customer" v-model="pay.customer" type="text" /></label>
          <label for="pay-phone">{{ t('pos.phone') }}<input id="pay-phone" v-model="pay.phone" type="tel" /></label>
        </div>
        <label for="pay-rx">{{ t('pos.rxPhoto') }}
          <input id="pay-rx" type="file" accept="image/*" capture="environment" @change="pay.rx = $event.target.files[0] || null" />
        </label>

        <div v-if="hasControlled && !catalog?.can_approve" class="approve">
          <p class="warn-text">{{ t('pos.controlled') }}</p>
          <div class="two">
            <label for="pay-approver">{{ t('pos.approver') }}<input id="pay-approver" v-model="pay.approver" type="text" autocomplete="off" /></label>
            <label for="pay-approver-pw">{{ t('pos.approverPassword') }}<input id="pay-approver-pw" v-model="pay.approverPassword" type="password" autocomplete="off" /></label>
          </div>
        </div>

        <p v-if="payError" class="error">{{ payError }}</p>
        <div class="actions">
          <button class="ghost" type="button" @click="paying = false">{{ t('common.cancel') }}</button>
          <button class="primary" type="submit" :disabled="!due.enough || busy">{{ t('pos.complete') }}</button>
        </div>
      </form>
    </div>
  </div>

  <div v-if="lastSale" class="print-only">
    <PosReceipt :sale="lastSale" :settings="settings" />
  </div>
</template>

<style scoped>
.pos { display: flex; flex-direction: column; gap: 12px; }
.pos-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; font-size: 13px; }
.spacer { flex: 1; }
.muted { color: #52606d; }
.small { font-size: 12px; }
.center { text-align: center; }
.pill { display: inline-block; padding: 2px 8px; border-radius: 99px; font-size: 12px; background: #e4e7eb; }
.pill.ok { background: #d1fae5; color: #065f46; }
.pill.off { background: #fee2e2; color: #991b1b; }
.pill.warn { background: #fef3c7; color: #92400e; }
.row-between { display: flex; justify-content: space-between; gap: 12px; }
.pos-grid { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 16px; align-items: start; }
@media (max-width: 900px) { .pos-grid { grid-template-columns: 1fr; } }
.left { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.scan { position: relative; }
.scan-input { width: 100%; font-size: 18px; padding: 12px 14px; border: 2px solid var(--accent); border-radius: 8px; }
.results { position: absolute; z-index: 5; left: 0; right: 0; top: 100%; list-style: none; margin: 4px 0 0; padding: 4px; background: #fff; border: 1px solid var(--border); border-radius: 8px; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); }
.results button { width: 100%; display: flex; justify-content: space-between; gap: 12px; padding: 8px 10px; border: none; background: none; text-align: left; border-radius: 6px; }
.results button:hover, .results button:focus-visible { background: #f0f4f8; }
.message { margin: 0; color: #92400e; }
.cart { overflow-x: auto; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.qty { display: inline-flex; align-items: center; gap: 4px; }
.qty input { width: 56px; text-align: center; padding: 4px; }
.qty button { width: 28px; height: 28px; border: 1px solid var(--border); background: #fff; border-radius: 6px; }
.small-input { width: 80px; padding: 4px 6px; text-align: right; }
.right { position: sticky; top: 12px; display: flex; flex-direction: column; gap: 10px; background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.sum-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-variant-numeric: tabular-nums; }
.grand { display: flex; flex-direction: column; align-items: flex-end; padding: 10px 0; border-top: 1px solid var(--border); }
.grand strong { font-size: 32px; color: var(--accent); font-variant-numeric: tabular-nums; }
.riel { font-size: 18px; font-variant-numeric: tabular-nums; }
.warn-text { color: #92400e; margin: 0; font-size: 13px; }
button.primary { background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 10px 16px; font-weight: 600; }
button.primary:disabled { opacity: 0.5; }
button.big { font-size: 20px; padding: 14px; }
button.ghost { background: none; border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; }
.last { display: flex; justify-content: space-between; font-size: 13px; }
.error { color: #b91c1c; margin: 0; }
.overlay { position: fixed; inset: 0; z-index: 20; background: rgba(15, 23, 42, 0.45); display: grid; place-items: center; padding: 16px; }
.dialog { background: #fff; border-radius: 12px; width: min(560px, 100%); max-height: 90vh; overflow: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.dialog h3 { margin: 0; }
.dialog label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.dialog input[type='text'], .dialog input[type='tel'], .dialog input[type='number'], .dialog input[type='password'] { padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 16px; }
.pay-row { display: flex; flex-direction: column; gap: 8px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.methods { display: flex; gap: 6px; flex-wrap: wrap; }
.methods button { padding: 8px 14px; border: 1px solid var(--border); border-radius: 8px; background: #fff; }
.methods button.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.change { font-size: 18px; padding: 10px; border-radius: 8px; background: #ecfdf5; }
.change.bad { background: #fef2f2; color: #b91c1c; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
@media (max-width: 500px) { .two { grid-template-columns: 1fr; } }
.approve { border: 1px solid #fcd34d; background: #fffbeb; border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; }
.print-only { display: none; }
</style>

<style>
@media print {
  @page { margin: 0; size: auto; }
  body * { visibility: hidden; }
  .print-only, .print-only * { visibility: visible; }
  .print-only { display: block !important; position: absolute; left: 0; top: 0; }
}
</style>
