from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.catalog.models import ProductUnit

from .models import ExchangeRate, Payment, Sale, SaleItem, ShopSettings


class ShopSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSettings
        fields = [
            "shop_name", "shop_name_km", "address", "phone", "receipt_footer",
            "receipt_width", "vat_enabled", "vat_rate", "expiry_alert_days",
        ]


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ["id", "khr_per_usd", "effective_at", "created_by"]
        read_only_fields = ["effective_at", "created_by"]


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product_unit.product.__str__", read_only=True)
    unit_name = serializers.CharField(source="product_unit.unit.name", read_only=True)
    unit_name_km = serializers.CharField(source="product_unit.unit.name_km", read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            "id", "product_unit", "product_name", "unit_name", "unit_name_km", "qty",
            "base_qty", "unit_price", "discount", "line_total",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["method", "amount", "currency", "amount_usd", "reference"]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source="cashier.username", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    total_khr = serializers.DecimalField(max_digits=16, decimal_places=0, read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id", "number", "client_uuid", "sale_type", "status", "branch", "branch_name",
            "cashier", "cashier_name", "approved_by", "customer_name", "customer_phone",
            "subtotal", "discount", "vat_rate", "vat_amount", "total", "total_khr", "paid",
            "change_usd", "exchange_rate", "note", "sold_at", "created_at",
            "voided_at", "void_reason", "items", "payments", "prescription_image",
        ]
        read_only_fields = fields


class LineInputSerializer(serializers.Serializer):
    product_unit = serializers.PrimaryKeyRelatedField(
        queryset=ProductUnit.objects.select_related("product", "unit")
    )
    qty = serializers.IntegerField(min_value=1)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)


class PaymentInputSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    reference = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")


class CheckoutSerializer(serializers.Serializer):
    client_uuid = serializers.UUIDField()
    lines = LineInputSerializer(many=True)
    payments = PaymentInputSerializer(many=True)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    sold_at = serializers.DateTimeField(required=False)
    customer_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    customer_phone = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    approver_username = serializers.CharField(required=False, allow_blank=True)
    approver_password = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        username = attrs.pop("approver_username", "")
        password = attrs.pop("approver_password", "")
        attrs["approver"] = None
        if username:
            approver = authenticate(username=username, password=password)
            if approver is None:
                raise serializers.ValidationError({"approver_username": "Wrong pharmacist login"})
            attrs["approver"] = approver
        return attrs


class VoidSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
