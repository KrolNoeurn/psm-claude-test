import axios from 'axios'

// Base URL of the Django API. In development Vite proxies /api to Django.
const http = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401, try the refresh token once, then send the user back to login.
http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const refresh = localStorage.getItem('refresh')
    if (error.response?.status === 401 && refresh && !original._retried) {
      original._retried = true
      try {
        const { data } = await axios.post(`${http.defaults.baseURL}/auth/token/refresh/`, { refresh })
        localStorage.setItem('access', data.access)
        return http(original)
      } catch {
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export default http
