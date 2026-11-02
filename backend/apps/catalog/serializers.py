from rest_framework import serializers

from .models import Category, Manufacturer, PriceTier, Product, ProductPrice, ProductUnit, Unit


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent"]


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ["id", "name", "country"]


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ["id", "name", "name_km"]


class PriceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceTier
        fields = ["id", "code", "name", "is_wholesale"]


class ProductPriceSerializer(serializers.ModelSerializer):
    tier_code = serializers.CharField(source="tier.code", read_only=True)

    class Meta:
        model = ProductPrice
        fields = ["id", "product_unit", "tier", "tier_code", "price", "min_qty"]


class ProductUnitSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    prices = ProductPriceSerializer(many=True, read_only=True)

    class Meta:
        model = ProductUnit
        fields = ["id", "product", "unit", "unit_name", "factor", "barcode", "is_base", "prices"]


class ProductSerializer(serializers.ModelSerializer):
    units = ProductUnitSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "sku", "generic_name", "brand_name", "dosage_form", "strength",
            "category", "manufacturer", "is_prescription_required", "is_controlled",
            "reorder_level", "is_active", "units",
        ]
