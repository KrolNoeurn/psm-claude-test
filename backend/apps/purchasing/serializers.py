from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import Branch
from apps.catalog.models import ProductUnit

from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine, Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id", "code", "name", "contact_name", "phone", "email", "address", "tax_id",
            "payment_terms_days", "note", "is_active", "created_at",
        ]
        read_only_fields = ["created_at"]


def _check_unit(attrs):
    unit = attrs.get("product_unit")
    product = attrs.get("product")
    if unit and product and unit.product_id != product.pk:
        raise serializers.ValidationError(
            {"product_unit": f"This unit does not belong to {product}."}
        )


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source="product.__str__", read_only=True)
    unit_name = serializers.CharField(source="product_unit.unit.name", read_only=True)
    factor = serializers.IntegerField(source="product_unit.factor", read_only=True)
    base_qty = serializers.IntegerField(read_only=True)
    remaining_base_qty = serializers.IntegerField(read_only=True)
    line_total = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    qty = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=0)

    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id", "product", "product_name", "product_unit", "unit_name", "factor", "qty",
            "unit_price", "line_total", "base_qty", "received_base_qty", "remaining_base_qty",
        ]
        read_only_fields = ["received_base_qty"]

    def validate(self, attrs):
        _check_unit(attrs)
        return attrs


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "number", "supplier", "supplier_name", "branch", "branch_name", "status",
            "order_date", "expected_date", "note", "lines", "total", "created_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["number", "status", "created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        if self.instance and self.instance.status != PurchaseOrder.Status.DRAFT:
            raise serializers.ValidationError("Only a draft purchase order can be edited.")
        if "lines" in attrs and not attrs["lines"]:
            raise serializers.ValidationError({"lines": "Add at least one line."})
        supplier = attrs.get("supplier")
        if supplier and not supplier.is_active and (
            not self.instance or self.instance.supplier_id != supplier.pk
        ):
            raise serializers.ValidationError({"supplier": "This supplier is inactive."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines")
        order = PurchaseOrder.objects.create(**validated_data)
        PurchaseOrderLine.objects.bulk_create(
            PurchaseOrderLine(order=order, **line) for line in lines
        )
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        instance = super().update(instance, validated_data)
        if lines is not None:
            # A draft's lines are replaced as a whole; nothing has been received yet.
            instance.lines.all().delete()
            PurchaseOrderLine.objects.bulk_create(
                PurchaseOrderLine(order=instance, **line) for line in lines
            )
        return instance


class GoodsReceiptLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.__str__", read_only=True)
    unit_name = serializers.CharField(source="product_unit.unit.name", read_only=True)
    factor = serializers.IntegerField(source="product_unit.factor", read_only=True)
    line_total = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)

    class Meta:
        model = GoodsReceiptLine
        fields = [
            "id", "order_line", "product", "product_name", "product_unit", "unit_name",
            "factor", "qty", "unit_cost", "line_total", "batch_no", "expiry_date",
            "base_qty", "base_unit_cost", "batch",
        ]
        read_only_fields = fields


class GoodsReceiptSerializer(serializers.ModelSerializer):
    lines = GoodsReceiptLineSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    purchase_order_number = serializers.CharField(
        source="purchase_order.number", read_only=True, default=None
    )
    total = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id", "number", "supplier", "supplier_name", "branch", "branch_name",
            "purchase_order", "purchase_order_number", "received_date",
            "supplier_invoice_no", "note", "lines", "total", "received_by", "created_at",
        ]
        read_only_fields = fields


class ReceiptLineInputSerializer(serializers.Serializer):
    order_line = serializers.PrimaryKeyRelatedField(
        queryset=PurchaseOrderLine.objects.all(), required=False, allow_null=True
    )
    product_unit = serializers.PrimaryKeyRelatedField(
        queryset=ProductUnit.objects.select_related("product")
    )
    qty = serializers.IntegerField(min_value=1, help_text="Quantity in the received unit")
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=0, help_text="Cost per received unit"
    )
    batch_no = serializers.CharField(max_length=60)
    expiry_date = serializers.DateField()


class PostGoodsReceiptSerializer(serializers.Serializer):
    """Input for posting a goods receipt. The product comes from the unit."""

    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())
    purchase_order = serializers.PrimaryKeyRelatedField(
        queryset=PurchaseOrder.objects.all(), required=False, allow_null=True
    )
    received_date = serializers.DateField(required=False)
    supplier_invoice_no = serializers.CharField(max_length=60, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    lines = ReceiptLineInputSerializer(many=True, allow_empty=False)
