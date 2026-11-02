from django.contrib import admin

from .models import Category, Manufacturer, PriceTier, Product, ProductPrice, ProductUnit, Unit


class ProductUnitInline(admin.TabularInline):
    model = ProductUnit
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "generic_name", "brand_name", "strength", "dosage_form", "is_active"]
    search_fields = ["sku", "generic_name", "brand_name"]
    list_filter = ["dosage_form", "is_prescription_required", "is_controlled"]
    inlines = [ProductUnitInline]


@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ["product_unit", "tier", "price", "min_qty"]
    list_filter = ["tier"]


admin.site.register([Category, Manufacturer, Unit, PriceTier])
