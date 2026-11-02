<script setup>
// Create a new purchase order or edit a draft.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import http from '../../api/http'
import ProductPicker from '../../components/ProductPicker.vue'
import { useAuthStore } from '../../stores/auth'
import { apiError, lineTotal, money, toBase } from '../../utils/purchasing'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const id = route.params.id
const suppliers = ref([])
const branches = ref([])
const error = ref('')
const busy = ref(false)
const order = ref({ supplier: '', branch: '', order_date: '', expected_date: '', note: '', lines: [] })

const total = computed(() => order.value.lines.reduce((s, l) => s + lineTotal(l.qty, l.unit_price), 0))

onMounted(async () => {
  const [s, b] = await Promise.all([
    http.get('/suppliers/', { params: { is_active: true } }),
    http.get('/branches/'),
  ])
  suppliers.value = s.data.results
  branches.value = b.data.results
  if (id) {
    const { data } = await http.get(`/purchase-orders/${id}/`)
    // Load each product's units so the unit dropdown works when editing.
    const products = await Promise.all(data.lines.map((l) => http.get(`/products/${l.product}/`)))
    data.lines = data.lines.map((l, i) => ({ ...l, units: products[i].data.units }))
    order.value = data
  } else {
    if (!auth.user) await auth.fetchMe().catch(() => {})
    order.value.branch = auth.user?.branch?.id || branches.value[0]?.id || ''
  }
})

function addProduct(p) {
  const units = p.units
  const biggest = [...units].sort((a, b) => b.factor - a.factor)[0]
  order.value.lines.push({
    product: p.id, product_name: `${p.brand_name || p.generic_name} ${p.strength}`.trim(),
    units, product_unit: biggest?.id, qty: 1, unit_price: '0',
  })
}

function factorOf(line) {
  return line.units?.find((u) => u.id === line.product_unit)?.factor || 0
}

async function save() {
  error.value = ''
  if (!order.value.lines.length) {
    error.value = t('purchasing.errors.noLines')
    return
  }
  busy.value = true
  const o = order.value
  const body = {
    supplier: o.supplier, branch: o.branch, expected_date: o.expected_date || null, note: o.note,
    ...(o.order_date ? { order_date: o.order_date } : {}),
    lines: o.lines.map((l) => ({ product: l.product, product_unit: l.product_unit, qty: l.qty, unit_price: l.unit_price })),
  }
  try {
    const { data } = id ? await http.put(`/purchase-orders/${id}/`, body) : await http.post('/purchase-orders/', body)
    router.push({ name: 'po-detail', params: { id: data.id } })
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="toolbar">
    <h2>{{ id ? `${t('purchasing.editOrder')} ${order.number || ''}` : t('purchasing.newOrder') }}</h2>
  </div>
  <p v-if="error" class="notice error">{{ error }}</p>
  <form class="panel" @submit.prevent="save">
    <div class="form-grid">
      <label>{{ t('purchasing.supplier') }} *
        <select v-model="order.supplier" required>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} - {{ s.name }}</option>
        </select>
      </label>
      <label>{{ t('purchasing.branch') }} *
        <select v-model="order.branch" required>
          <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.code }} - {{ b.name }}</option>
        </select>
      </label>
      <label>{{ t('purchasing.orderDate') }}<input v-model="order.order_date" type="date" /></label>
      <label>{{ t('purchasing.expectedDate') }}<input v-model="order.expected_date" type="date" /></label>
      <label>{{ t('common.note') }}<textarea v-model="order.note" rows="1" /></label>
    </div>

    <h3>{{ t('purchasing.lines') }}</h3>
    <table class="grid">
      <thead>
        <tr><th>{{ t('purchasing.product') }}</th><th>{{ t('purchasing.unit') }}</th><th class="num">{{ t('purchasing.qty') }}</th><th class="num">{{ t('purchasing.price') }}</th><th class="num">{{ t('purchasing.baseQty') }}</th><th class="num">{{ t('purchasing.lineTotal') }}</th><th /></tr>
      </thead>
      <tbody>
        <tr v-for="(l, i) in order.lines" :key="i">
          <td>{{ l.product_name }}</td>
          <td>
            <select v-model="l.product_unit">
              <option v-for="u in l.units" :key="u.id" :value="u.id">{{ u.unit_name }} (×{{ u.factor }})</option>
            </select>
          </td>
          <td class="num"><input v-model.number="l.qty" class="num" type="number" min="1" required /></td>
          <td class="num"><input v-model="l.unit_price" class="num" type="number" min="0" step="0.0001" required /></td>
          <td class="num">{{ toBase(l.qty, factorOf(l)) }}</td>
          <td class="num">{{ money(lineTotal(l.qty, l.unit_price)) }}</td>
          <td><button type="button" class="link" @click="order.lines.splice(i, 1)">{{ t('common.remove') }}</button></td>
        </tr>
        <tr v-if="!order.lines.length"><td colspan="7">{{ t('common.empty') }}</td></tr>
        <tr class="total-row"><td colspan="5">{{ t('common.total') }}</td><td class="num">{{ money(total) }}</td><td /></tr>
      </tbody>
    </table>
    <ProductPicker @pick="addProduct" />

    <div class="actions">
      <button class="btn" type="submit" :disabled="busy">{{ t('purchasing.saveDraft') }}</button>
      <button class="btn secondary" type="button" @click="router.back()">{{ t('common.cancel') }}</button>
    </div>
  </form>
</template>
