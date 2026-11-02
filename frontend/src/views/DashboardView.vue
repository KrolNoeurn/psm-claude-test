<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '../api/http'

const { t } = useI18n()
const productCount = ref('–')
const expiringCount = ref('–')

onMounted(async () => {
  const [products, expiring] = await Promise.all([
    http.get('/products/'),
    http.get('/stock/batches/expiring/', { params: { days: 30 } }),
  ])
  productCount.value = products.data.count
  expiringCount.value = expiring.data.count
})
</script>

<template>
  <h2>{{ t('nav.dashboard') }}</h2>
  <div class="tiles">
    <div class="tile"><span class="label">{{ t('nav.products') }}</span><span class="value">{{ productCount }}</span></div>
    <div class="tile warn"><span class="label">{{ t('stock.expiring') }}</span><span class="value">{{ expiringCount }}</span></div>
  </div>
</template>
