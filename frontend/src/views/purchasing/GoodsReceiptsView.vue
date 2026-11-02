<script setup>
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import http from '../../api/http'
import { money } from '../../utils/purchasing'

const { t } = useI18n()
const route = useRoute()
const receipts = ref([])
const search = ref('')
const openId = ref(null)

async function load() {
  const { data } = await http.get('/goods-receipts/', { params: { search: search.value || undefined } })
  receipts.value = data.results
}

let timer
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})
onMounted(load)
</script>

<template>
  <div class="toolbar">
    <h2>{{ t('nav.goodsReceipts') }}</h2>
    <span class="spacer" />
    <RouterLink class="btn secondary" :to="{ name: 'grn-new' }">{{ t('purchasing.directReceipt') }}</RouterLink>
  </div>
  <p v-if="route.query.posted" class="notice">{{ t('purchasing.posted', { number: route.query.posted }) }}</p>
  <input v-model="search" class="search" :placeholder="t('common.search')" />
  <table class="grid">
    <thead>
      <tr><th>{{ t('purchasing.number') }}</th><th>{{ t('purchasing.receivedDate') }}</th><th>{{ t('purchasing.supplier') }}</th><th>{{ t('purchasing.branch') }}</th><th>{{ t('purchasing.fromOrder') }}</th><th>{{ t('purchasing.invoiceNo') }}</th><th class="num">{{ t('common.total') }}</th></tr>
    </thead>
    <tbody>
      <template v-for="r in receipts" :key="r.id">
        <tr class="clickable" @click="openId = openId === r.id ? null : r.id">
          <td>{{ r.number }}</td>
          <td>{{ r.received_date }}</td>
          <td>{{ r.supplier_name }}</td>
          <td>{{ r.branch_name }}</td>
          <td>
            <RouterLink v-if="r.purchase_order" :to="{ name: 'po-detail', params: { id: r.purchase_order } }" @click.stop>{{ r.purchase_order_number }}</RouterLink>
          </td>
          <td>{{ r.supplier_invoice_no }}</td>
          <td class="num">{{ money(r.total) }}</td>
        </tr>
        <tr v-if="openId === r.id">
          <td colspan="7">
            <table class="grid">
              <thead>
                <tr><th>{{ t('purchasing.product') }}</th><th class="num">{{ t('purchasing.qty') }}</th><th>{{ t('purchasing.unit') }}</th><th>{{ t('purchasing.batch') }}</th><th>{{ t('purchasing.expiry') }}</th><th class="num">{{ t('purchasing.baseQty') }}</th><th class="num">{{ t('purchasing.perBase') }}</th><th class="num">{{ t('purchasing.lineTotal') }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="l in r.lines" :key="l.id">
                  <td>{{ l.product_name }}</td>
                  <td class="num">{{ l.qty }}</td>
                  <td>{{ l.unit_name }}</td>
                  <td>{{ l.batch_no }}</td>
                  <td>{{ l.expiry_date }}</td>
                  <td class="num">{{ l.base_qty }}</td>
                  <td class="num">{{ l.base_unit_cost }}</td>
                  <td class="num">{{ money(l.line_total) }}</td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
      </template>
      <tr v-if="!receipts.length"><td colspan="7">{{ t('common.empty') }}</td></tr>
    </tbody>
  </table>
</template>
