from django.contrib import admin

from .models import StockBatch, StockMovement


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ["product", "branch", "batch_no", "expiry_date", "qty_on_hand"]
    list_filter = ["branch"]
    search_fields = ["batch_no", "product__generic_name"]
    readonly_fields = ["qty_on_hand"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["created_at", "batch", "kind", "qty", "user"]
    list_filter = ["kind"]

    def has_change_permission(self, request, obj=None):
        return False  # the ledger is append-only
