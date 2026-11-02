<script setup>
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import http from '../../api/http'
import StatusBadge from '../../components/StatusBadge.vue'
import { money } from '../../utils/purchasing'

const { t } = useI18n()
const router = useRouter()
const orders = ref([])
const status = ref('')
const search = ref('')
const statuses = ['draft', 'ordered', 'partial', 'received', 'cancelled']

async function load() {
  const { data } = await http.get('/purchase-orders/', {
    params: { status: status.value || undefined, search: search.value || undefined },
  })
  orders.value = data.results
}

let timer
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})
watch(status, load)
onMounted(load)
</script>

<template>
  <div class="toolbar">
    <h2>{{ t('nav.purchaseOrders') }}</h2>
    <span class="spacer" />
    <RouterLink class="btn" :to="{ name: 'po-new' }">{{ t('purchasing.newOrder') }}</RouterLink>
  </div>
  <div class="toolbar">
    <input v-model="search" class="search" :placeholder="t('common.search')" />
    <select v-model="status">
      <option value="">{{ t('common.all') }}</option>
      <option v-for="s in statuses" :key="s" :value="s">{{ t(`purchasing.status_${s}`) }}</option>
    </select>
  </div>
  <table class="grid">
    <thead>
      <tr><th>{{ t('purchasing.number') }}</th><th>{{ t('purchasing.supplier') }}</th><th>{{ t('purchasing.branch') }}</th><th>{{ t('purchasing.orderDate') }}</th><th>{{ t('purchasing.expectedDate') }}</th><th>{{ t('purchasing.status') }}</th><th class="num">{{ t('common.total') }}</th></tr>
    </thead>
    <tbody>
      <tr v-for="o in orders" :key="o.id" class="clickable" @click="router.push({ name: 'po-detail', params: { id: o.id } })">
        <td>{{ o.number }}</td>
        <td>{{ o.supplier_name }}</td>
        <td>{{ o.branch_name }}</td>
        <td>{{ o.order_date }}</td>
        <td>{{ o.expected_date || '' }}</td>
        <td><StatusBadge :status="o.status" /></td>
        <td class="num">{{ money(o.total) }}</td>
      </tr>
      <tr v-if="!orders.length"><td colspan="7">{{ t('common.empty') }}</td></tr>
    </tbody>
  </table>
</template>
