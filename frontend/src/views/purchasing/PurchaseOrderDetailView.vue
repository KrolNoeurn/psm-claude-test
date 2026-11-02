<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import http from '../../api/http'
import StatusBadge from '../../components/StatusBadge.vue'
import { apiError, money } from '../../utils/purchasing'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const order = ref(null)
const receipts = ref([])
const error = ref('')
const busy = ref(false)

const canReceive = computed(() => ['ordered', 'partial'].includes(order.value?.status))

async function load() {
  const id = route.params.id
  const [o, r] = await Promise.all([
    http.get(`/purchase-orders/${id}/`),
    http.get('/goods-receipts/', { params: { purchase_order: id } }),
  ])
  order.value = o.data
  receipts.value = r.data.results
}
onMounted(load)

async function act(action, confirmFirst = false) {
  if (confirmFirst && !window.confirm(t('common.confirm'))) return
  error.value = ''
  busy.value = true
  try {
    const { data } = await http.post(`/purchase-orders/${order.value.id}/${action}/`)
    order.value = data
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!window.confirm(t('common.confirm'))) return
  try {
    await http.delete(`/purchase-orders/${order.value.id}/`)
    router.push({ name: 'po-list' })
  } catch (e) {
    error.value = apiError(e)
  }
}
</script>

<template>
  <template v-if="order">
    <div class="toolbar">
      <h2>{{ order.number }}</h2>
      <StatusBadge :status="order.status" />
      <span class="spacer" />
      <RouterLink class="btn secondary" :to="{ name: 'po-list' }">{{ t('common.back') }}</RouterLink>
    </div>
    <p v-if="error" class="notice error">{{ error }}</p>

    <div class="panel">
      <div class="meta">
        <div><span>{{ t('purchasing.supplier') }}:</span> {{ order.supplier_name }}</div>
        <div><span>{{ t('purchasing.branch') }}:</span> {{ order.branch_name }}</div>
        <div><span>{{ t('purchasing.orderDate') }}:</span> {{ order.order_date }}</div>
        <div v-if="order.expected_date"><span>{{ t('purchasing.expectedDate') }}:</span> {{ order.expected_date }}</div>
      </div>
      <p v-if="order.note">{{ order.note }}</p>

      <table class="grid">
        <thead>
          <tr><th>{{ t('purchasing.product') }}</th><th class="num">{{ t('purchasing.qty') }}</th><th>{{ t('purchasing.unit') }}</th><th class="num">{{ t('purchasing.price') }}</th><th class="num">{{ t('purchasing.lineTotal') }}</th><th class="num">{{ t('purchasing.baseQty') }}</th><th class="num">{{ t('purchasing.received') }}</th><th class="num">{{ t('purchasing.remaining') }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="l in order.lines" :key="l.id">
            <td>{{ l.product_name }}</td>
            <td class="num">{{ l.qty }}</td>
            <td>{{ l.unit_name }} (×{{ l.factor }})</td>
            <td class="num">{{ money(l.unit_price) }}</td>
            <td class="num">{{ money(l.line_total) }}</td>
            <td class="num">{{ l.base_qty }}</td>
            <td class="num">{{ l.received_base_qty }}</td>
            <td class="num">{{ l.remaining_base_qty }}</td>
          </tr>
          <tr class="total-row"><td colspan="4">{{ t('common.total') }}</td><td class="num">{{ money(order.total) }}</td><td colspan="3" /></tr>
        </tbody>
      </table>

      <div class="actions">
        <template v-if="order.status === 'draft'">
          <RouterLink class="btn secondary" :to="{ name: 'po-edit', params: { id: order.id } }">{{ t('common.edit') }}</RouterLink>
          <button class="btn" :disabled="busy" @click="act('submit')">{{ t('purchasing.submit') }}</button>
          <button class="btn danger" :disabled="busy" @click="remove">{{ t('common.delete') }}</button>
        </template>
        <RouterLink v-if="canReceive" class="btn" :to="{ name: 'grn-new', query: { po: order.id } }">{{ t('purchasing.receive') }}</RouterLink>
        <button v-if="order.status === 'ordered'" class="btn danger" :disabled="busy" @click="act('cancel', true)">{{ t('purchasing.cancelOrder') }}</button>
        <button v-if="order.status === 'partial'" class="btn secondary" :disabled="busy" @click="act('close', true)">{{ t('purchasing.closeOrder') }}</button>
      </div>
    </div>

    <h3 v-if="receipts.length">{{ t('purchasing.receipts') }}</h3>
    <table v-if="receipts.length" class="grid">
      <thead>
        <tr><th>{{ t('purchasing.number') }}</th><th>{{ t('purchasing.receivedDate') }}</th><th>{{ t('purchasing.invoiceNo') }}</th><th>{{ t('purchasing.lines') }}</th><th class="num">{{ t('common.total') }}</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in receipts" :key="r.id">
          <td>{{ r.number }}</td>
          <td>{{ r.received_date }}</td>
          <td>{{ r.supplier_invoice_no }}</td>
          <td>
            <div v-for="l in r.lines" :key="l.id">{{ l.product_name }}: {{ l.qty }} {{ l.unit_name }} · #{{ l.batch_no }} · {{ l.expiry_date }}</div>
          </td>
          <td class="num">{{ money(r.total) }}</td>
        </tr>
      </tbody>
    </table>
  </template>
  <p v-else>{{ t('common.loading') }}</p>
</template>
