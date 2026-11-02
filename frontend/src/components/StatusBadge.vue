<script setup>
import { useI18n } from 'vue-i18n'

defineProps({ status: { type: String, required: true } })
const { t } = useI18n()
</script>

<template>
  <span class="badge" :class="`badge-${status}`">{{ t(`purchasing.status_${status}`) }}</span>
</template>
