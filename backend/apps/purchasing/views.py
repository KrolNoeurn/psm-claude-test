from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine, Supplier
from .permissions import CanManagePurchasing
from .serializers import (
    GoodsReceiptSerializer, PostGoodsReceiptSerializer, PurchaseOrderSerializer,
    SupplierSerializer,
)


def _rule_error(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [CanManagePurchasing]
    search_fields = ["code", "name", "contact_name", "phone"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "code"]

    def destroy(self, request, *args, **kwargs):
        supplier = self.get_object()
        if supplier.orders.exists() or supplier.receipts.exists():
            return _rule_error("This supplier has documents; mark it inactive instead.")
        return super().destroy(request, *args, **kwargs)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = (
        PurchaseOrder.objects.select_related("supplier", "branch")
        .prefetch_related(Prefetch(
            "lines",
            queryset=PurchaseOrderLine.objects.select_related("product", "product_unit__unit"),
        ))
    )
    serializer_class = PurchaseOrderSerializer
    permission_classes = [CanManagePurchasing]
    filterset_fields = ["status", "supplier", "branch"]
    search_fields = ["number", "supplier__name", "note"]
    ordering_fields = ["order_date", "created_at", "number"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().status != PurchaseOrder.Status.DRAFT:
            return _rule_error("Only a draft purchase order can be deleted; cancel it instead.")
        return super().destroy(request, *args, **kwargs)

    def _transition(self, func):
        try:
            order = func(self.get_object())
        except services.PurchasingError as exc:
            return _rule_error(exc)
        return Response(self.get_serializer(self.get_queryset().get(pk=order.pk)).data)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Draft -> Ordered."""
        return self._transition(services.submit_order)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._transition(services.cancel_order)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Mark a partially received PO as finished."""
        return self._transition(services.close_order)


class GoodsReceiptViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Goods receipts are posted once and never edited or deleted."""

    queryset = (
        GoodsReceipt.objects.select_related("supplier", "branch", "purchase_order")
        .prefetch_related(Prefetch(
            "lines",
            queryset=GoodsReceiptLine.objects.select_related("product", "product_unit__unit"),
        ))
    )
    serializer_class = GoodsReceiptSerializer
    permission_classes = [CanManagePurchasing]
    filterset_fields = ["supplier", "branch", "purchase_order"]
    search_fields = ["number", "supplier__name", "supplier_invoice_no", "lines__batch_no"]
    ordering_fields = ["received_date", "created_at"]

    @extend_schema(request=PostGoodsReceiptSerializer, responses=GoodsReceiptSerializer)
    def create(self, request, *args, **kwargs):
        data = PostGoodsReceiptSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        lines = [
            services.ReceiptLineInput(
                product=line["product_unit"].product, product_unit=line["product_unit"],
                qty=line["qty"], unit_cost=line["unit_cost"], batch_no=line["batch_no"],
                expiry_date=line["expiry_date"], order_line=line.get("order_line"),
            )
            for line in v["lines"]
        ]
        try:
            receipt = services.post_goods_receipt(
                supplier=v["supplier"], branch=v["branch"], lines=lines, user=request.user,
                purchase_order=v.get("purchase_order"), received_date=v.get("received_date"),
                supplier_invoice_no=v.get("supplier_invoice_no", ""), note=v.get("note", ""),
            )
        except services.PurchasingError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        receipt = self.get_queryset().get(pk=receipt.pk)
        return Response(self.get_serializer(receipt).data, status=status.HTTP_201_CREATED)
