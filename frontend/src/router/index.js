import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../layouts/AppLayout.vue'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
      { path: 'pos', name: 'pos', component: () => import('../views/PosView.vue') },
      { path: 'products', name: 'products', component: () => import('../views/ProductsView.vue') },
      { path: 'stock', name: 'stock', component: () => import('../views/StockView.vue') },
      { path: 'purchasing/suppliers', name: 'suppliers', component: () => import('../views/purchasing/SuppliersView.vue') },
      { path: 'purchasing/orders', name: 'po-list', component: () => import('../views/purchasing/PurchaseOrdersView.vue') },
      { path: 'purchasing/orders/new', name: 'po-new', component: () => import('../views/purchasing/PurchaseOrderFormView.vue') },
      { path: 'purchasing/orders/:id', name: 'po-detail', component: () => import('../views/purchasing/PurchaseOrderDetailView.vue') },
      { path: 'purchasing/orders/:id/edit', name: 'po-edit', component: () => import('../views/purchasing/PurchaseOrderFormView.vue') },
      { path: 'purchasing/receipts', name: 'grn-list', component: () => import('../views/purchasing/GoodsReceiptsView.vue') },
      { path: 'purchasing/receipts/new', name: 'grn-new', component: () => import('../views/purchasing/GoodsReceiptFormView.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) return { name: 'login', query: { next: to.fullPath } }
})

export default router
