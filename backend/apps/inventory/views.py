from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Branch
from apps.catalog.models import Product

from . import services
from .models import StockBatch, StockMovement
from .serializers import (
    AdjustStockSerializer, ReceiveStockSerializer, StockBatchSerializer,
    StockMovementSerializer,
)


class StockBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """Batches are read-only here; stock changes go through the actions below."""

    queryset = StockBatch.objects.select_related("product", "branch")
    serializer_class = StockBatchSerializer
    filterset_fields = ["product", "branch"]
    search_fields = ["batch_no", "product__generic_name", "product__brand_name"]
    ordering_fields = ["expiry_date", "qty_on_hand"]

    @action(detail=False, methods=["post"])
    def receive(self, request):
        data = ReceiveStockSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        batch = services.receive_stock(
            product=get_object_or_404(Product, pk=v["product"]),
            branch=get_object_or_404(Branch, pk=v["branch"]),
            batch_no=v["batch_no"], expiry_date=v["expiry_date"],
            unit_cost=v["unit_cost"], qty=v["qty"], user=request.user,
            ref_type="manual",
        )
        return Response(StockBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        data = AdjustStockSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        batch = services.adjust_stock(
            batch=self.get_object(), new_qty=data.validated_data["new_qty"],
            user=request.user, note=data.validated_data.get("note", ""),
        )
        return Response(StockBatchSerializer(batch).data)

    @action(detail=False, methods=["get"], url_path="expiring")
    def expiring(self, request):
        """Batches with stock that expire within `days` (default 90)."""
        days = int(request.query_params.get("days", 90))
        limit = timezone.localdate() + timedelta(days=days)
        qs = self.filter_queryset(self.get_queryset()).filter(
            qty_on_hand__gt=0, expiry_date__lte=limit
        )
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(StockBatchSerializer(page, many=True).data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("batch")
    serializer_class = StockMovementSerializer
    filterset_fields = ["batch", "batch__product", "batch__branch", "kind"]
