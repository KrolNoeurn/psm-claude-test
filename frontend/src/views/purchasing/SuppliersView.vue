<script setup>
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '../../api/http'
import { apiError } from '../../utils/purchasing'

const { t } = useI18n()
const suppliers = ref([])
const search = ref('')
const editing = ref(null) // null = form closed; {} = new; supplier = edit
const error = ref('')

const blank = () => ({ code: '', name: '', contact_name: '', phone: '', email: '', address: '', tax_id: '', payment_terms_days: 0, note: '', is_active: true })

async function load() {
  const { data } = await http.get('/suppliers/', { params: { search: search.value || undefined } })
  suppliers.value = data.results
}

let timer
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})
onMounted(load)

function open(s) {
  error.value = ''
  editing.value = s ? { ...s } : blank()
}

async function save() {
  error.value = ''
  try {
    const s = editing.value
    if (s.id) await http.put(`/suppliers/${s.id}/`, s)
    else await http.post('/suppliers/', s)
    editing.value = null
    await load()
  } catch (e) {
    error.value = apiError(e)
  }
}
</script>

<template>
  <div class="toolbar">
    <h2>{{ t('nav.suppliers') }}</h2>
    <span class="spacer" />
    <button class="btn" @click="open(null)">{{ t('purchasing.newSupplier') }}</button>
  </div>

  <form v-if="editing" class="panel" @submit.prevent="save">
    <h3>{{ editing.id ? t('purchasing.editSupplier') : t('purchasing.newSupplier') }}</h3>
    <p v-if="error" class="notice error">{{ error }}</p>
    <div class="form-grid">
      <label>{{ t('purchasing.code') }} *<input v-model="editing.code" required /></label>
      <label>{{ t('purchasing.name') }} *<input v-model="editing.name" required /></label>
      <label>{{ t('purchasing.contact') }}<input v-model="editing.contact_name" /></label>
      <label>{{ t('purchasing.phone') }}<input v-model="editing.phone" /></label>
      <label>{{ t('purchasing.email') }}<input v-model="editing.email" type="email" /></label>
      <label>{{ t('purchasing.taxId') }}<input v-model="editing.tax_id" /></label>
      <label>{{ t('purchasing.terms') }}<input v-model.number="editing.payment_terms_days" type="number" min="0" /></label>
      <label>{{ t('purchasing.address') }}<textarea v-model="editing.address" rows="2" /></label>
      <label>{{ t('common.note') }}<textarea v-model="editing.note" rows="2" /></label>
      <label class="field"><span><input v-model="editing.is_active" type="checkbox" /> {{ t('common.active') }}</span></label>
    </div>
    <div class="actions">
      <button class="btn" type="submit">{{ t('common.save') }}</button>
      <button class="btn secondary" type="button" @click="editing = null">{{ t('common.cancel') }}</button>
    </div>
  </form>

  <input v-model="search" class="search" :placeholder="t('common.search')" />
  <table class="grid">
    <thead>
      <tr><th>{{ t('purchasing.code') }}</th><th>{{ t('purchasing.name') }}</th><th>{{ t('purchasing.contact') }}</th><th>{{ t('purchasing.phone') }}</th><th class="num">{{ t('purchasing.terms') }}</th><th>{{ t('common.active') }}</th></tr>
    </thead>
    <tbody>
      <tr v-for="s in suppliers" :key="s.id" class="clickable" @click="open(s)">
        <td>{{ s.code }}</td>
        <td>{{ s.name }}</td>
        <td>{{ s.contact_name }}</td>
        <td>{{ s.phone }}</td>
        <td class="num">{{ s.payment_terms_days }}</td>
        <td>{{ s.is_active ? '✓' : '' }}</td>
      </tr>
      <tr v-if="!suppliers.length"><td colspan="6">{{ t('common.empty') }}</td></tr>
    </tbody>
  </table>
</template>
