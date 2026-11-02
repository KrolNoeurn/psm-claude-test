import { defineStore } from 'pinia'
import http from '../api/http'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null }),
  getters: {
    isLoggedIn: () => !!localStorage.getItem('access'),
  },
  actions: {
    async login(username, password) {
      const { data } = await http.post('/auth/token/', { username, password })
      localStorage.setItem('access', data.access)
      localStorage.setItem('refresh', data.refresh)
      await this.fetchMe()
    },
    async fetchMe() {
      const { data } = await http.get('/auth/me/')
      this.user = data
    },
    logout() {
      localStorage.removeItem('access')
      localStorage.removeItem('refresh')
      this.user = null
    },
  },
})
