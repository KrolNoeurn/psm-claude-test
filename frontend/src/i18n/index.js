import { createI18n } from 'vue-i18n'

const messages = {
  en: {
    appName: 'Pharmacy PMS',
    nav: { dashboard: 'Dashboard', pos: 'POS (Retail)', products: 'Products', stock: 'Stock & Expiry' },
    login: { title: 'Sign in', username: 'Username', password: 'Password', submit: 'Sign in', failed: 'Wrong username or password' },
    common: { logout: 'Log out', search: 'Search', loading: 'Loading…', empty: 'No data' },
    products: { sku: 'SKU', name: 'Name', strength: 'Strength', form: 'Form', units: 'Units', rx: 'Rx' },
    stock: { batch: 'Batch', expiry: 'Expiry', qty: 'Qty (base unit)', daysLeft: 'Days left', expiring: 'Expiring within 90 days' },
    pos: { comingSoon: 'The POS screen is built in Phase 1, sprint 4.' },
  },
  km: {
    appName: 'ប្រព័ន្ធឱសថស្ថាន',
    nav: { dashboard: 'ផ្ទាំងគ្រប់គ្រង', pos: 'លក់រាយ (POS)', products: 'ផលិតផល', stock: 'ស្តុក និងថ្ងៃផុតកំណត់' },
    login: { title: 'ចូលប្រព័ន្ធ', username: 'ឈ្មោះអ្នកប្រើ', password: 'ពាក្យសម្ងាត់', submit: 'ចូល', failed: 'ឈ្មោះ ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ' },
    common: { logout: 'ចាកចេញ', search: 'ស្វែងរក', loading: 'កំពុងផ្ទុក…', empty: 'គ្មានទិន្នន័យ' },
    products: { sku: 'SKU', name: 'ឈ្មោះ', strength: 'កម្លាំង', form: 'ទម្រង់', units: 'ឯកតា', rx: 'វេជ្ជបញ្ជា' },
    stock: { batch: 'Batch', expiry: 'ថ្ងៃផុតកំណត់', qty: 'ចំនួន (ឯកតាមូលដ្ឋាន)', daysLeft: 'ថ្ងៃនៅសល់', expiring: 'ផុតកំណត់ក្នុង 90 ថ្ងៃ' },
    pos: { comingSoon: 'អេក្រង់ POS នឹងបង្កើតក្នុង Phase 1, sprint ទី 4។' },
  },
}

export default createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'km',
  fallbackLocale: 'en',
  messages,
})
