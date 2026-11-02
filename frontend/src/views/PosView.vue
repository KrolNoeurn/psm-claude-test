<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <h2>{{ t('nav.pos') }}</h2>
  <p>{{ t('pos.comingSoon') }}</p>
</template>
