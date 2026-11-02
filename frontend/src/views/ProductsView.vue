<script setup>
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '../api/http'

const { t } = useI18n()
const products = ref([])
const search = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/products/', { params: { search: search.value || undefined } })
    products.value = data.results
  } finally {
    loading.value = false
  }
}

let timer
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})
onMounted(load)
</script>

<template>
  <h2>{{ t('nav.products') }}</h2>
  <input v-model="search" class="search" :placeholder="t('common.search')" />
  <p v-if="loading">{{ t('common.loading') }}</p>
  <table v-else class="grid">
    <thead>
      <tr><th>{{ t('products.sku') }}</th><th>{{ t('products.name') }}</th><th>{{ t('products.strength') }}</th><th>{{ t('products.form') }}</th><th>{{ t('products.units') }}</th><th>{{ t('products.rx') }}</th></tr>
    </thead>
    <tbody>
      <tr v-for="p in products" :key="p.id">
        <td>{{ p.sku }}</td>
        <td>{{ p.brand_name || p.generic_name }} <small v-if="p.brand_name">({{ p.generic_name }})</small></td>
        <td>{{ p.strength }}</td>
        <td>{{ p.dosage_form }}</td>
        <td>{{ p.units.map((u) => `${u.unit_name} ×${u.factor}`).join(', ') }}</td>
        <td>{{ p.is_prescription_required ? '✓' : '' }}</td>
      </tr>
      <tr v-if="!products.length"><td colspan="6">{{ t('common.empty') }}</td></tr>
    </tbody>
  </table>
</template>
