<script setup>
// Type to search products; emits the chosen product (with its units).
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '../api/http'

const emit = defineEmits(['pick'])
const { t } = useI18n()
const query = ref('')
const results = ref([])
let timer

watch(query, (q) => {
  clearTimeout(timer)
  if (!q.trim()) {
    results.value = []
    return
  }
  timer = setTimeout(async () => {
    const { data } = await http.get('/products/', { params: { search: q, is_active: true } })
    results.value = data.results
  }, 250)
})

function pick(p) {
  emit('pick', p)
  query.value = ''
  results.value = []
}
</script>

<template>
  <div class="picker">
    <input v-model="query" class="search" :placeholder="t('purchasing.searchProduct')" />
    <ul v-if="results.length" class="picker-list">
      <li v-for="p in results" :key="p.id" @click="pick(p)">
        <strong>{{ p.brand_name || p.generic_name }}</strong> {{ p.strength }}
        <small>{{ p.sku }} · {{ p.units.map((u) => `${u.unit_name} ×${u.factor}`).join(', ') }}</small>
      </li>
    </ul>
  </div>
</template>
