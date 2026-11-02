from rest_framework import serializers

from .models import StockBatch, StockMovement


class StockBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.__str__", read_only=True)

    class Meta:
        model = StockBatch
        fields = [
            "id", "product", "product_name", "branch", "batch_no", "expiry_date",
            "unit_cost", "qty_on_hand", "received_at",
        ]
        # Quantity changes only through services (receipts, sales, adjustments).
        read_only_fields = ["qty_on_hand", "received_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            "id", "batch", "kind", "qty", "ref_type", "ref_id", "note", "user", "created_at",
        ]
        read_only_fields = fields


class ReceiveStockSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    branch = serializers.IntegerField()
    batch_no = serializers.CharField(max_length=60)
    expiry_date = serializers.DateField()
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=4)
    qty = serializers.IntegerField(min_value=1, help_text="Base units")


class AdjustStockSerializer(serializers.Serializer):
    new_qty = serializers.IntegerField(min_value=0)
    note = serializers.CharField(max_length=255, allow_blank=True, required=False)
