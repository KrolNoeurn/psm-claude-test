<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '../api/http'
import { daysUntil, expiryStatus } from '../utils/expiry'

const { t } = useI18n()
const batches = ref([])

onMounted(async () => {
  const { data } = await http.get('/stock/batches/', { params: { ordering: 'expiry_date' } })
  batches.value = data.results
})
</script>

<template>
  <h2>{{ t('nav.stock') }}</h2>
  <table class="grid">
    <thead>
      <tr><th>{{ t('products.name') }}</th><th>{{ t('stock.batch') }}</th><th>{{ t('stock.expiry') }}</th><th>{{ t('stock.daysLeft') }}</th><th>{{ t('stock.qty') }}</th></tr>
    </thead>
    <tbody>
      <tr v-for="b in batches" :key="b.id" :class="expiryStatus(b.expiry_date)">
        <td>{{ b.product_name }}</td>
        <td>{{ b.batch_no }}</td>
        <td>{{ b.expiry_date }}</td>
        <td>{{ daysUntil(b.expiry_date) }}</td>
        <td>{{ b.qty_on_hand }}</td>
      </tr>
      <tr v-if="!batches.length"><td colspan="5">{{ t('common.empty') }}</td></tr>
    </tbody>
  </table>
</template>
