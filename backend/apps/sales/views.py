import json

from django.db.models import Count, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.accounts.models import User

from . import services
from .models import ExchangeRate, Sale, ShopSettings
from .serializers import (
    CheckoutSerializer, ExchangeRateSerializer, SaleSerializer, ShopSettingsSerializer,
    VoidSerializer,
)

MANAGER_ROLES = {User.Role.ADMIN, User.Role.MANAGER}


class ReadAllWriteManagers(BasePermission):
    message = "Only a manager can change this setting."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or user.is_superuser or user.role in MANAGER_ROLES


def user_branch(user):
    if user.branch_id is None:
        raise ValidationError({"branch": "Your account has no branch. Ask a manager to set one."})
    return user.branch


@extend_schema(request=ShopSettingsSerializer, responses=ShopSettingsSerializer)
@api_view(["GET", "PUT", "PATCH"])
def shop_settings(request):
    obj = ShopSettings.load()
    if request.method == "GET":
        return Response(ShopSettingsSerializer(obj).data)
    if not (request.user.is_superuser or request.user.role in MANAGER_ROLES):
        raise PermissionDenied("Only a manager can change shop settings.")
    ser = ShopSettingsSerializer(obj, data=request.data, partial=request.method == "PATCH")
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@extend_schema(responses=None)
@api_view(["GET"])
def pos_catalog(request):
    """Products, units, retail prices and sellable stock for the cashier's branch.

    The POS keeps this in the browser so it can keep selling when the
    internet drops.
    """
    branch = user_branch(request.user)
    return Response({
        "branch": {"id": branch.id, "code": branch.code, "name": branch.name},
        "exchange_rate": str(ExchangeRate.current()),
        "settings": ShopSettingsSerializer(ShopSettings.load()).data,
        "can_approve": services.can_approve(request.user),
        "generated_at": timezone.now(),
        "products": services.pos_catalog(branch),
    })


class ExchangeRateViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                          viewsets.GenericViewSet):
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [ReadAllWriteManagers]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SaleViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = (
        Sale.objects.select_related("branch", "cashier")
        .prefetch_related("items__product_unit__product", "items__product_unit__unit", "payments")
    )
    serializer_class = SaleSerializer
    filterset_fields = ["branch", "status", "sale_type", "cashier"]
    search_fields = ["number", "customer_name", "customer_phone"]
    ordering_fields = ["sold_at", "total"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # Staff below manager only see their own branch.
        if not (user.is_superuser or user.role in MANAGER_ROLES):
            qs = qs.filter(branch_id=user.branch_id)
        return qs

    @extend_schema(request=CheckoutSerializer, responses=SaleSerializer)
    def create(self, request):
        # A sale with a prescription photo arrives as multipart: photo + "data" JSON.
        payload = request.data
        if "data" in request.data and hasattr(request.data, "getlist"):
            try:
                payload = json.loads(request.data["data"])
            except ValueError:
                raise ValidationError({"data": "Invalid JSON"})
        ser = CheckoutSerializer(data=payload)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        data = services.SaleInput(
            client_uuid=v["client_uuid"],
            branch=user_branch(request.user),
            cashier=request.user,
            lines=[services.LineInput(**line) for line in v["lines"]],
            payments=[services.PaymentInput(**p) for p in v["payments"]],
            discount=v["discount"],
            approver=v["approver"],
            sold_at=v.get("sold_at"),
            customer_name=v["customer_name"],
            customer_phone=v["customer_phone"],
            note=v["note"],
            prescription_image=request.FILES.get("prescription_image"),
        )
        try:
            sale, created = services.create_sale(data)
        except services.SaleError as e:
            return Response({"detail": str(e), "code": e.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            SaleSerializer(sale, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(request=VoidSerializer, responses=SaleSerializer)
    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        ser = VoidSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            sale = services.void_sale(
                sale=self.get_object(), user=request.user, reason=ser.validated_data["reason"]
            )
        except services.SaleError as e:
            code = status.HTTP_403_FORBIDDEN if e.code == "forbidden" else status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(e), "code": e.code}, status=code)
        return Response(SaleSerializer(sale, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def today(self, request):
        """Today's completed sales total for the cashier's view of branches."""
        today = timezone.localdate()
        qs = self.get_queryset().filter(status=Sale.Status.COMPLETED, sold_at__date=today)
        agg = qs.aggregate(count=Count("id"), total=Sum("total"))
        return Response({"date": today, "count": agg["count"], "total": agg["total"] or 0})
