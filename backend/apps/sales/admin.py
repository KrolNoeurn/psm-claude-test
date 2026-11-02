from django.contrib import admin

from .models import ExchangeRate, Payment, Sale, SaleItem, ShopSettings


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = [f.name for f in SaleItem._meta.fields]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = [f.name for f in Payment._meta.fields]


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ["number", "sold_at", "branch", "cashier", "total", "status"]
    list_filter = ["status", "branch", "sale_type"]
    search_fields = ["number", "customer_name"]
    inlines = [SaleItemInline, PaymentInline]

    def has_change_permission(self, request, obj=None):
        return False  # sales change only through void


admin.site.register([ShopSettings, ExchangeRate])
