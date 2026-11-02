import { createI18n } from 'vue-i18n'

const messages = {
  en: {
    appName: 'Pharmacy PMS',
    nav: { dashboard: 'Dashboard', pos: 'POS (Retail)', products: 'Products', stock: 'Stock & Expiry', purchasing: 'Purchasing', suppliers: 'Suppliers', purchaseOrders: 'Purchase orders', goodsReceipts: 'Goods receipts' },
    login: { title: 'Sign in', username: 'Username', password: 'Password', submit: 'Sign in', failed: 'Wrong username or password' },
    common: { logout: 'Log out', search: 'Search', loading: 'Loading…', empty: 'No data', save: 'Save', cancel: 'Cancel', edit: 'Edit', delete: 'Delete', add: 'Add', back: 'Back', new: 'New', all: 'All', confirm: 'Are you sure?', saved: 'Saved', active: 'Active', note: 'Note', total: 'Total', date: 'Date', remove: 'Remove' },
    products: { sku: 'SKU', name: 'Name', strength: 'Strength', form: 'Form', units: 'Units', rx: 'Rx' },
    stock: { batch: 'Batch', expiry: 'Expiry', qty: 'Qty (base unit)', daysLeft: 'Days left', expiring: 'Expiring within 90 days' },
    pos: { comingSoon: 'The POS screen is built in Phase 1, sprint 4.' },
    purchasing: {
      supplier: 'Supplier', code: 'Code', name: 'Name', contact: 'Contact person', phone: 'Phone', email: 'Email',
      address: 'Address', taxId: 'VAT / tax ID', terms: 'Credit days', newSupplier: 'New supplier', editSupplier: 'Edit supplier',
      number: 'Number', branch: 'Branch', status: 'Status', orderDate: 'Order date', expectedDate: 'Expected date',
      newOrder: 'New purchase order', editOrder: 'Edit purchase order', lines: 'Items', product: 'Product', unit: 'Unit',
      qty: 'Qty', price: 'Price / unit', cost: 'Cost / unit', lineTotal: 'Amount', baseQty: 'Base units',
      received: 'Received', remaining: 'Still to come', addLine: 'Add item', searchProduct: 'Search product name, SKU or barcode…',
      saveDraft: 'Save draft', submit: 'Send to supplier', cancelOrder: 'Cancel PO', closeOrder: 'Close (rest will not come)',
      receive: 'Receive goods', newReceipt: 'Receive goods', directReceipt: 'Receive without PO', fromOrder: 'From purchase order',
      invoiceNo: 'Supplier invoice no.', receivedDate: 'Received date', batch: 'Batch no.', expiry: 'Expiry date',
      splitBatch: 'Another batch', post: 'Post receipt and add to stock', posted: 'Receipt {number} posted. Stock updated.',
      receipts: 'Receipts', receivedBy: 'Received by', perBase: 'cost / base unit',
      status_draft: 'Draft', status_ordered: 'Ordered', status_partial: 'Partly received', status_received: 'Received', status_cancelled: 'Cancelled',
      errors: {
        unit: 'choose a unit', qty: 'quantity must be more than 0', batch: 'batch no. is required', expiryMissing: 'expiry date is required',
        expired: 'this batch is already expired', tooMany: 'more than is still on order', noLines: 'Add at least one item.',
      },
    },
  },
  km: {
    appName: 'ប្រព័ន្ធឱសថស្ថាន',
    nav: { dashboard: 'ផ្ទាំងគ្រប់គ្រង', pos: 'លក់រាយ (POS)', products: 'ផលិតផល', stock: 'ស្តុក និងថ្ងៃផុតកំណត់', purchasing: 'ការទិញចូល', suppliers: 'អ្នកផ្គត់ផ្គង់', purchaseOrders: 'បញ្ជាទិញ (PO)', goodsReceipts: 'ការទទួលទំនិញ' },
    login: { title: 'ចូលប្រព័ន្ធ', username: 'ឈ្មោះអ្នកប្រើ', password: 'ពាក្យសម្ងាត់', submit: 'ចូល', failed: 'ឈ្មោះ ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ' },
    common: { logout: 'ចាកចេញ', search: 'ស្វែងរក', loading: 'កំពុងផ្ទុក…', empty: 'គ្មានទិន្នន័យ', save: 'រក្សាទុក', cancel: 'បោះបង់', edit: 'កែប្រែ', delete: 'លុប', add: 'បន្ថែម', back: 'ត្រឡប់ក្រោយ', new: 'បង្កើតថ្មី', all: 'ទាំងអស់', confirm: 'តើអ្នកប្រាកដទេ?', saved: 'បានរក្សាទុក', active: 'សកម្ម', note: 'កំណត់សម្គាល់', total: 'សរុប', date: 'កាលបរិច្ឆេទ', remove: 'ដកចេញ' },
    products: { sku: 'SKU', name: 'ឈ្មោះ', strength: 'កម្លាំង', form: 'ទម្រង់', units: 'ឯកតា', rx: 'វេជ្ជបញ្ជា' },
    stock: { batch: 'Batch', expiry: 'ថ្ងៃផុតកំណត់', qty: 'ចំនួន (ឯកតាមូលដ្ឋាន)', daysLeft: 'ថ្ងៃនៅសល់', expiring: 'ផុតកំណត់ក្នុង 90 ថ្ងៃ' },
    pos: { comingSoon: 'អេក្រង់ POS នឹងបង្កើតក្នុង Phase 1, sprint ទី 4។' },
    purchasing: {
      supplier: 'អ្នកផ្គត់ផ្គង់', code: 'លេខកូដ', name: 'ឈ្មោះ', contact: 'អ្នកទំនាក់ទំនង', phone: 'ទូរស័ព្ទ', email: 'អ៊ីមែល',
      address: 'អាសយដ្ឋាន', taxId: 'លេខ VAT / ពន្ធ', terms: 'ចំនួនថ្ងៃជំពាក់', newSupplier: 'អ្នកផ្គត់ផ្គង់ថ្មី', editSupplier: 'កែអ្នកផ្គត់ផ្គង់',
      number: 'លេខ', branch: 'សាខា', status: 'ស្ថានភាព', orderDate: 'ថ្ងៃបញ្ជាទិញ', expectedDate: 'ថ្ងៃរំពឹងទទួល',
      newOrder: 'បញ្ជាទិញថ្មី', editOrder: 'កែបញ្ជាទិញ', lines: 'មុខទំនិញ', product: 'ផលិតផល', unit: 'ឯកតា',
      qty: 'ចំនួន', price: 'តម្លៃ / ឯកតា', cost: 'ថ្លៃដើម / ឯកតា', lineTotal: 'ទឹកប្រាក់', baseQty: 'ឯកតាមូលដ្ឋាន',
      received: 'បានទទួល', remaining: 'នៅខ្វះ', addLine: 'បន្ថែមមុខទំនិញ', searchProduct: 'ស្វែងរកឈ្មោះ SKU ឬ barcode…',
      saveDraft: 'រក្សាទុកសេចក្តីព្រាង', submit: 'ផ្ញើទៅអ្នកផ្គត់ផ្គង់', cancelOrder: 'បោះបង់ PO', closeOrder: 'បិទ (ដែលនៅសល់មិនមកទៀត)',
      receive: 'ទទួលទំនិញ', newReceipt: 'ទទួលទំនិញ', directReceipt: 'ទទួលដោយគ្មាន PO', fromOrder: 'ពីបញ្ជាទិញ',
      invoiceNo: 'លេខវិក្កយបត្រអ្នកផ្គត់ផ្គង់', receivedDate: 'ថ្ងៃទទួល', batch: 'លេខ Batch', expiry: 'ថ្ងៃផុតកំណត់',
      splitBatch: 'Batch មួយទៀត', post: 'កត់ត្រា និងបញ្ចូលស្តុក', posted: 'បានកត់ត្រា {number}។ ស្តុកត្រូវបានធ្វើបច្ចុប្បន្នភាព។',
      receipts: 'ការទទួល', receivedBy: 'អ្នកទទួល', perBase: 'ថ្លៃដើម / ឯកតាមូលដ្ឋាន',
      status_draft: 'សេចក្តីព្រាង', status_ordered: 'បានបញ្ជាទិញ', status_partial: 'ទទួលបានខ្លះ', status_received: 'ទទួលរួច', status_cancelled: 'បានបោះបង់',
      errors: {
        unit: 'សូមជ្រើសឯកតា', qty: 'ចំនួនត្រូវតែធំជាង 0', batch: 'ត្រូវការលេខ Batch', expiryMissing: 'ត្រូវការថ្ងៃផុតកំណត់',
        expired: 'Batch នេះផុតកំណត់ហើយ', tooMany: 'លើសចំនួនដែលនៅខ្វះក្នុង PO', noLines: 'សូមបន្ថែមមុខទំនិញយ៉ាងហោចណាស់មួយ។',
      },
    },
  },
}

export default createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'km',
  fallbackLocale: 'en',
  messages,
})
