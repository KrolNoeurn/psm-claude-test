from rest_framework import viewsets

from .models import Category, Manufacturer, PriceTier, Product, ProductPrice, ProductUnit, Unit
from .serializers import (
    CategorySerializer, ManufacturerSerializer, PriceTierSerializer, ProductPriceSerializer,
    ProductSerializer, ProductUnitSerializer, UnitSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]


class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    search_fields = ["name"]


class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


class PriceTierViewSet(viewsets.ModelViewSet):
    queryset = PriceTier.objects.all()
    serializer_class = PriceTierSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.prefetch_related("units__unit", "units__prices__tier")
    serializer_class = ProductSerializer
    search_fields = ["sku", "generic_name", "brand_name", "units__barcode"]
    filterset_fields = ["category", "dosage_form", "is_active", "is_prescription_required"]
    ordering_fields = ["generic_name", "sku"]


class ProductUnitViewSet(viewsets.ModelViewSet):
    queryset = ProductUnit.objects.select_related("unit").prefetch_related("prices")
    serializer_class = ProductUnitSerializer
    filterset_fields = ["product", "barcode"]


class ProductPriceViewSet(viewsets.ModelViewSet):
    queryset = ProductPrice.objects.select_related("tier")
    serializer_class = ProductPriceSerializer
    filterset_fields = ["product_unit", "tier"]
