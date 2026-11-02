from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.views import BranchViewSet, me
from apps.catalog import views as catalog
from apps.inventory import views as inventory
from apps.purchasing import views as purchasing

router = DefaultRouter()
router.register("branches", BranchViewSet)
router.register("categories", catalog.CategoryViewSet)
router.register("manufacturers", catalog.ManufacturerViewSet)
router.register("units", catalog.UnitViewSet)
router.register("price-tiers", catalog.PriceTierViewSet)
router.register("products", catalog.ProductViewSet)
router.register("product-units", catalog.ProductUnitViewSet)
router.register("product-prices", catalog.ProductPriceViewSet)
router.register("stock/batches", inventory.StockBatchViewSet)
router.register("stock/movements", inventory.StockMovementViewSet)
router.register("suppliers", purchasing.SupplierViewSet)
router.register("purchase-orders", purchasing.PurchaseOrderViewSet)
router.register("goods-receipts", purchasing.GoodsReceiptViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", me, name="me"),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
