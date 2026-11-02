<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const { t, locale } = useI18n()

onMounted(() => {
  if (!auth.user) auth.fetchMe().catch(() => {})
})

function switchLocale() {
  locale.value = locale.value === 'km' ? 'en' : 'km'
  localStorage.setItem('locale', locale.value)
}

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <h1 class="brand">{{ t('appName') }}</h1>
      <nav>
        <RouterLink :to="{ name: 'dashboard' }">{{ t('nav.dashboard') }}</RouterLink>
        <RouterLink :to="{ name: 'pos' }">{{ t('nav.pos') }}</RouterLink>
        <RouterLink :to="{ name: 'products' }">{{ t('nav.products') }}</RouterLink>
        <RouterLink :to="{ name: 'stock' }">{{ t('nav.stock') }}</RouterLink>
        <div class="nav-group">{{ t('nav.purchasing') }}</div>
        <RouterLink :to="{ name: 'po-list' }">{{ t('nav.purchaseOrders') }}</RouterLink>
        <RouterLink :to="{ name: 'grn-list' }">{{ t('nav.goodsReceipts') }}</RouterLink>
        <RouterLink :to="{ name: 'suppliers' }">{{ t('nav.suppliers') }}</RouterLink>
      </nav>
    </aside>
    <div class="main">
      <header class="topbar">
        <span v-if="auth.user">{{ auth.user.username }} · {{ auth.user.role }}</span>
        <span class="spacer" />
        <button class="link" @click="switchLocale">{{ locale === 'km' ? 'English' : 'ខ្មែរ' }}</button>
        <button class="link" @click="logout">{{ t('common.logout') }}</button>
      </header>
      <main class="content"><RouterView /></main>
    </div>
  </div>
</template>
