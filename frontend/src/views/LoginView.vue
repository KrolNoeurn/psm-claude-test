<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push(route.query.next || '/')
  } catch {
    error.value = t('login.failed')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="login">
    <form class="card" @submit.prevent="submit">
      <h1>{{ t('appName') }}</h1>
      <h2>{{ t('login.title') }}</h2>
      <label>{{ t('login.username') }}<input v-model="username" autocomplete="username" required /></label>
      <label>{{ t('login.password') }}<input v-model="password" type="password" autocomplete="current-password" required /></label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="busy">{{ t('login.submit') }}</button>
    </form>
  </div>
</template>
