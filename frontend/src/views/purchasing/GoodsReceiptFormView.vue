<script setup>
// Receive goods, from a purchase order (?po=ID) or directly from a supplier.
// Each row is one batch: batch no. + expiry are required, and the quantity
// can be typed in any unit of the product (box, strip, tablet).
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import http from '../../api/http'
import ProductPicker from '../../components/ProductPicker.vue'
import { useAuthStore } from '../../stores/auth'
import {
  apiError, convertCost, describeBase, isoDate, lineTotal, money, suggestReceipt, toBase, validateReceiptRows,
} from '../../utils/purchasing'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const poId = route.query.po
const order = ref(null)
const suppliers = ref([])
const branches = ref([])
const header = ref({ supplier: '', branch: '', received_date: isoDate(new Date()), supplier_invoice_no: '', note: '' })
const rows = ref([])
const error = ref('')
const busy = ref(false)

const errors = computed(() => validateReceiptRows(rows.value.map(withFactor)))
const rowHasError = (i) => errors.value.some((e) => e.row === i)
const total = computed(() => rows.value.reduce((s, r) => s + lineTotal(r.qty, r.unit_cost), 0))

function withFactor(r) {
  const unit = r.units.find((u) => u.id === r.product_unit)
  return { ...r, factor: unit?.factor || 0 }
}

onMounted(async () => {
  const [s, b] = await Promise.all([http.get('/suppliers/', { params: { is_active: true } }), http.get('/branches/')])
  suppliers.value = s.data.results
  branches.value = b.data.results
  if (poId) {
    const { data } = await http.get(`/purchase-orders/${poId}/`)
    order.value = data
    header.value.supplier = data.supplier
    header.value.branch = data.branch
    const open = data.lines.filter((l) => l.remaining_base_qty > 0)
    const products = await Promise.all(open.map((l) => http.get(`/products/${l.product}/`)))
    rows.value = open.map((l, i) => {
      const units = products[i].data.units
      const ordered = units.find((u) => u.id === l.product_unit)
      const s = suggestReceipt(l.remaining_base_qty, ordered, units)
      return {
        order_line: l.id, product_name: l.product_name, units, remaining_base_qty: l.remaining_base_qty,
        product_unit: s.unitId, qty: s.qty, unit_cost: String(convertCost(l.unit_price, l.factor, s.factor)),
        batch_no: '', expiry_date: '', _price: { cost: l.unit_price, factor: l.factor },
      }
    })
  } else {
    if (!auth.user) await auth.fetchMe().catch(() => {})
    header.value.branch = auth.user?.branch?.id || branches.value[0]?.id || ''
  }
})

function addProduct(p) {
  const biggest = [...p.units].sort((a, b) => b.factor - a.factor)[0]
  rows.value.push({
    order_line: null, product_name: `${p.brand_name || p.generic_name} ${p.strength}`.trim(), units: p.units,
    product_unit: biggest?.id, qty: 1, unit_cost: '0', batch_no: '', expiry_date: '',
  })
}

// Split a PO line into another batch row (same product, different lot).
function splitRow(i) {
  const r = rows.value[i]
  rows.value.splice(i + 1, 0, { ...r, qty: 0, batch_no: '', expiry_date: '' })
}

// Keep the price per unit right when the unit changes (box price -> strip price).
function onUnitChange(r) {
  if (!r._price) return
  const unit = r.units.find((u) => u.id === r.product_unit)
  r.unit_cost = String(convertCost(r._price.cost, r._price.factor, unit.factor))
}

const errorText = (i) => errors.value.filter((e) => e.row === i).map((e) => t(`purchasing.errors.${e.key}`)).join(', ')

async function post() {
  error.value = ''
  const active = rows.value.filter((r) => Number(r.qty) > 0)
  if (!active.length) {
    error.value = t('purchasing.errors.noLines')
    return
  }
  if (validateReceiptRows(active.map(withFactor)).length) return
  busy.value = true
  try {
    const { data } = await http.post('/goods-receipts/', {
      ...header.value,
      purchase_order: order.value?.id || null,
      lines: active.map((r) => ({
        order_line: r.order_line, product_unit: r.product_unit, qty: r.qty, unit_cost: r.unit_cost,
        batch_no: r.batch_no, expiry_date: r.expiry_date,
      })),
    })
    router.push({ name: 'grn-list', query: { posted: data.number } })
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="toolbar">
    <h2>{{ order ? `${t('purchasing.newReceipt')} · ${order.number}` : t('purchasing.directReceipt') }}</h2>
  </div>
  <p v-if="error" class="notice error">{{ error }}</p>

  <form class="panel" @submit.prevent="post">
    <div class="form-grid">
      <label>{{ t('purchasing.supplier') }} *
        <select v-model="header.supplier" required :disabled="!!order">
          <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} - {{ s.name }}</option>
          <option v-if="order && !suppliers.some((s) => s.id === order.supplier)" :value="order.supplier">{{ order.supplier_name }}</option>
        </select>
      </label>
      <label>{{ t('purchasing.branch') }} *
        <select v-model="header.branch" required :disabled="!!order">
          <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.code }} - {{ b.name }}</option>
        </select>
      </label>
      <label>{{ t('purchasing.receivedDate') }}<input v-model="header.received_date" type="date" /></label>
      <label>{{ t('purchasing.invoiceNo') }}<input v-model="header.supplier_invoice_no" /></label>
      <label>{{ t('common.note') }}<textarea v-model="header.note" rows="1" /></label>
    </div>

    <h3>{{ t('purchasing.lines') }}</h3>
    <table class="grid">
      <thead>
        <tr>
          <th>{{ t('purchasing.product') }}</th><th>{{ t('purchasing.unit') }}</th><th class="num">{{ t('purchasing.qty') }}</th>
          <th class="num">{{ t('purchasing.cost') }}</th><th>{{ t('purchasing.batch') }} *</th><th>{{ t('purchasing.expiry') }} *</th>
          <th class="num">{{ t('purchasing.baseQty') }}</th><th class="num">{{ t('purchasing.lineTotal') }}</th><th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="(r, i) in rows" :key="i" :class="{ 'row-error': rowHasError(i) && r.qty > 0 }">
          <td>
            {{ r.product_name }}
            <small v-if="r.order_line">{{ t('purchasing.remaining') }}: {{ describeBase(r.remaining_base_qty, r.units) }}</small>
            <small v-if="rowHasError(i) && r.qty > 0" class="error">{{ errorText(i) }}</small>
          </td>
          <td>
            <select v-model="r.product_unit" @change="onUnitChange(r)">
              <option v-for="u in r.units" :key="u.id" :value="u.id">{{ u.unit_name }} (×{{ u.factor }})</option>
            </select>
          </td>
          <td class="num"><input v-model.number="r.qty" class="num" type="number" min="0" /></td>
          <td class="num"><input v-model="r.unit_cost" class="num" type="number" min="0" step="0.0001" /></td>
          <td><input v-model="r.batch_no" class="batch" /></td>
          <td><input v-model="r.expiry_date" type="date" /></td>
          <td class="num">{{ toBase(r.qty, withFactor(r).factor) }}</td>
          <td class="num">{{ money(lineTotal(r.qty, r.unit_cost)) }}</td>
          <td>
            <button v-if="r.order_line" type="button" class="link" @click="splitRow(i)">+ {{ t('purchasing.splitBatch') }}</button>
            <button v-else type="button" class="link" @click="rows.splice(i, 1)">{{ t('common.remove') }}</button>
          </td>
        </tr>
        <tr v-if="!rows.length"><td colspan="9">{{ t('common.empty') }}</td></tr>
        <tr class="total-row"><td colspan="7">{{ t('common.total') }}</td><td class="num">{{ money(total) }}</td><td /></tr>
      </tbody>
    </table>
    <ProductPicker v-if="!order" @pick="addProduct" />

    <div class="actions">
      <button class="btn" type="submit" :disabled="busy || !rows.length">{{ t('purchasing.post') }}</button>
      <button class="btn secondary" type="button" @click="router.back()">{{ t('common.cancel') }}</button>
    </div>
  </form>
</template>
