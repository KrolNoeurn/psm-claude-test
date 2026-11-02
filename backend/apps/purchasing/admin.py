from django.contrib import admin

from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "phone", "payment_terms_days", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "phone"]


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0
    readonly_fields = ["received_base_qty"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["number", "supplier", "branch", "status", "order_date"]
    list_filter = ["status", "branch"]
    search_fields = ["number", "supplier__name"]
    readonly_fields = ["number", "status"]
    inlines = [PurchaseOrderLineInline]


class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    """Read-only: receipts are posted through the API so stock stays correct."""

    list_display = ["number", "supplier", "branch", "purchase_order", "received_date"]
    list_filter = ["branch"]
    search_fields = ["number", "supplier__name", "supplier_invoice_no"]
    inlines = [GoodsReceiptLineInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
