<script setup>
// Printable receipt for 80 mm or 58 mm thermal printers, Khmer and English.
import { computed } from 'vue'

const props = defineProps({
  sale: { type: Object, required: true },
  settings: { type: Object, required: true },
})

const width = computed(() => (props.settings.receipt_width === '58' ? '58mm' : '80mm'))
const when = computed(() => new Date(props.sale.sold_at).toLocaleString('en-GB'))
const riel = (n) => Number(n).toLocaleString('en-US')
const methodLabel = { cash_usd: 'Cash / សាច់ប្រាក់ $', cash_khr: 'Cash / សាច់ប្រាក់ ៛', khqr: 'KHQR' }
</script>

<template>
  <div class="receipt" :style="{ width }">
    <div class="center">
      <strong class="shop">{{ settings.shop_name_km || settings.shop_name }}</strong>
      <div v-if="settings.shop_name_km">{{ settings.shop_name }}</div>
      <div v-if="settings.address">{{ settings.address }}</div>
      <div v-if="settings.phone">{{ settings.phone }}</div>
    </div>
    <hr />
    <div class="row"><span>លេខ / No.</span><span>{{ sale.number }}</span></div>
    <div class="row"><span>ថ្ងៃ / Date</span><span>{{ when }}</span></div>
    <div class="row"><span>អ្នកគិតលុយ / Cashier</span><span>{{ sale.cashier_name }}</span></div>
    <div v-if="sale.customer_name" class="row"><span>អតិថិជន / Customer</span><span>{{ sale.customer_name }}</span></div>
    <div v-if="sale.offline" class="center small">* Offline — រង់ចាំផ្ញើទៅ server *</div>
    <hr />
    <div v-for="(item, i) in sale.items" :key="i" class="item">
      <div>{{ item.product_name }}</div>
      <div class="row small">
        <span>{{ item.qty }} {{ item.unit_name_km || item.unit_name }} × ${{ item.unit_price }}<template v-if="Number(item.discount)"> − ${{ item.discount }}</template></span>
        <span>${{ item.line_total }}</span>
      </div>
    </div>
    <hr />
    <div class="row"><span>សរុបរង / Subtotal</span><span>${{ sale.subtotal }}</span></div>
    <div v-if="Number(sale.discount)" class="row"><span>បញ្ចុះ / Discount</span><span>−${{ sale.discount }}</span></div>
    <div v-if="Number(sale.vat_amount)" class="row"><span>VAT {{ Number(sale.vat_rate) }}%</span><span>${{ sale.vat_amount }}</span></div>
    <div class="row total"><span>សរុប / Total</span><span>${{ sale.total }}</span></div>
    <div class="row total"><span></span><span>{{ riel(sale.total_khr) }} ៛</span></div>
    <hr />
    <div v-for="(p, i) in sale.payments" :key="i" class="row small">
      <span>{{ methodLabel[p.method] }}</span>
      <span>{{ p.currency === 'KHR' ? riel(p.amount) + ' ៛' : '$' + Number(p.amount).toFixed(2) }}</span>
    </div>
    <div v-if="Number(sale.change_usd)" class="row"><span>ប្រាក់អាប់ / Change</span><span>${{ sale.change_usd }} · {{ riel(sale.change_riel ?? 0) }} ៛</span></div>
    <div class="row small"><span>អត្រា / Rate</span><span>1$ = {{ riel(sale.exchange_rate) }} ៛</span></div>
    <hr />
    <div class="center">{{ settings.receipt_footer }}</div>
  </div>
</template>

<style scoped>
.receipt { font-family: 'Noto Sans Khmer', system-ui, sans-serif; font-size: 12px; line-height: 1.45; color: #000; background: #fff; padding: 4mm 3mm; }
.center { text-align: center; }
.shop { font-size: 15px; }
.row { display: flex; justify-content: space-between; gap: 8px; }
.row span:last-child { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.small { font-size: 11px; }
.total { font-weight: 700; font-size: 14px; }
.item { margin-bottom: 3px; }
hr { border: none; border-top: 1px dashed #000; margin: 5px 0; }
</style>
