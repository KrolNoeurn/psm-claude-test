import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Branch, User
from apps.catalog.models import PriceTier, Product, ProductPrice, ProductUnit, Unit
from apps.inventory.models import StockBatch, StockMovement
from apps.inventory.services import receive_stock
from apps.sales.models import ExchangeRate, Sale, ShopSettings

TODAY = timezone.localdate()


@pytest.fixture
def branch(db):
    return Branch.objects.create(code="PP1", name="Phnom Penh 1")


@pytest.fixture
def retail(db):
    return PriceTier.objects.create(code="RETAIL", name="Retail")


def make_product(sku, retail, *, controlled=False):
    """1 box = 10 strips = 100 tablets; tablet $0.30, strip $2.50 ($2.20 from 5 strips)."""
    p = Product.objects.create(
        sku=sku, generic_name=sku.title(), dosage_form="tablet", is_controlled=controlled
    )
    tab, _ = Unit.objects.get_or_create(name="Tablet")
    strip, _ = Unit.objects.get_or_create(name="Strip")
    p.u_tab = ProductUnit.objects.create(product=p, unit=tab, factor=1, is_base=True,
                                         barcode=f"{sku}T")
    p.u_strip = ProductUnit.objects.create(product=p, unit=strip, factor=10, barcode=f"{sku}S")
    ProductPrice.objects.create(product_unit=p.u_tab, tier=retail, price=Decimal("0.30"))
    ProductPrice.objects.create(product_unit=p.u_strip, tier=retail, price=Decimal("2.50"))
    ProductPrice.objects.create(product_unit=p.u_strip, tier=retail, price=Decimal("2.20"),
                                min_qty=5)
    return p


@pytest.fixture
def para(branch, retail):
    p = make_product("PARA", retail)
    receive_stock(product=p, branch=branch, batch_no="LATE", expiry_date=TODAY + timedelta(days=400),
                  unit_cost=Decimal("0.10"), qty=100)
    receive_stock(product=p, branch=branch, batch_no="EARLY", expiry_date=TODAY + timedelta(days=40),
                  unit_cost=Decimal("0.12"), qty=15)
    return p


@pytest.fixture
def morphine(branch, retail):
    p = make_product("MORPH", retail, controlled=True)
    receive_stock(product=p, branch=branch, batch_no="M1", expiry_date=TODAY + timedelta(days=300),
                  unit_cost=Decimal("1.00"), qty=50)
    return p


def client_for(role, branch, username=None):
    user = User.objects.create_user(username or f"u_{role}", password="pass-1234-xyz",
                                    role=role, branch=branch)
    c = APIClient()
    c.force_authenticate(user)
    c.user = user
    return c


@pytest.fixture
def cashier(branch):
    return client_for(User.Role.CASHIER, branch)


def checkout(c, lines, payments, **extra):
    body = {"client_uuid": str(uuid.uuid4()), "lines": lines, "payments": payments, **extra}
    return c.post("/api/sales/", body, format="json")


def test_sale_takes_stock_fefo_and_records_cost(cashier, para):
    r = checkout(cashier, [{"product_unit": para.u_strip.id, "qty": 2}],
                 [{"method": "cash_usd", "amount": "10.00"}])
    assert r.status_code == 201, r.content
    sale = Sale.objects.get(number=r.json()["number"])
    assert sale.total == Decimal("5.00")
    assert sale.change_usd == Decimal("5.00")
    item = sale.items.get()
    assert item.base_qty == 20
    # 15 from the early batch first, then 5 from the late one.
    assert sorted((b.batch.batch_no, b.qty) for b in item.batches.all()) == [("EARLY", 15), ("LATE", 5)]
    assert item.cost == Decimal("15") * Decimal("0.12") + Decimal("5") * Decimal("0.10")
    assert StockBatch.objects.get(batch_no="EARLY").qty_on_hand == 0


def test_quantity_break_price(cashier, para):
    r = checkout(cashier, [{"product_unit": para.u_strip.id, "qty": 5}],
                 [{"method": "cash_usd", "amount": "11.00"}])
    assert r.status_code == 201, r.content
    assert Decimal(r.json()["total"]) == Decimal("11.00")


def test_riel_payment_with_rate(cashier, para):
    ExchangeRate.objects.create(khr_per_usd=Decimal("4100"))
    # Total $2.50 = 10,250 riel; customer pays 10,300 riel (100-riel steps).
    r = checkout(cashier, [{"product_unit": para.u_strip.id, "qty": 1}],
                 [{"method": "cash_khr", "amount": "10300"}])
    assert r.status_code == 201, r.content
    data = r.json()
    assert data["payments"][0]["currency"] == "KHR"
    assert Decimal(data["total_khr"]) == Decimal("10300")  # 10,250 rounded up to 100 riel
    assert Decimal(data["exchange_rate"]) == Decimal("4100")


def test_underpaid_sale_is_rejected_and_stock_untouched(cashier, para):
    r = checkout(cashier, [{"product_unit": para.u_strip.id, "qty": 1}],
                 [{"method": "cash_usd", "amount": "1.00"}])
    assert r.status_code == 400
    assert r.json()["code"] == "underpaid"
    assert Sale.objects.count() == 0
    assert StockBatch.objects.get(batch_no="EARLY").qty_on_hand == 15
    assert not StockMovement.objects.filter(kind=StockMovement.Kind.SALE).exists()


def test_insufficient_stock(cashier, para):
    r = checkout(cashier, [{"product_unit": para.u_strip.id, "qty": 20}],
                 [{"method": "cash_usd", "amount": "100"}])
    assert r.status_code == 400
    assert r.json()["code"] == "insufficient_stock"


def test_same_client_uuid_is_saved_once(cashier, para):
    body = {"client_uuid": str(uuid.uuid4()),
            "lines": [{"product_unit": para.u_tab.id, "qty": 3}],
            "payments": [{"method": "khqr", "amount": "0.90", "reference": "TX1"}]}
    first = cashier.post("/api/sales/", body, format="json")
    again = cashier.post("/api/sales/", body, format="json")
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["number"] == again.json()["number"]
    assert Sale.objects.count() == 1


def test_controlled_drug_needs_pharmacist(cashier, morphine, branch):
    lines = [{"product_unit": morphine.u_tab.id, "qty": 2}]
    pay = [{"method": "cash_usd", "amount": "1"}]
    r = checkout(cashier, lines, pay)
    assert r.status_code == 400 and r.json()["code"] == "approval_required"

    User.objects.create_user("pharm", password="pharm-pass-123", role=User.Role.PHARMACIST,
                             branch=branch)
    r = checkout(cashier, lines, pay, approver_username="pharm", approver_password="wrong")
    assert r.status_code == 400

    r = checkout(cashier, lines, pay, approver_username="pharm", approver_password="pharm-pass-123")
    assert r.status_code == 201, r.content
    assert Sale.objects.get().approved_by.username == "pharm"


def test_pharmacist_sells_controlled_without_extra_login(morphine, branch):
    c = client_for(User.Role.PHARMACIST, branch)
    r = checkout(c, [{"product_unit": morphine.u_tab.id, "qty": 1}],
                 [{"method": "cash_usd", "amount": "1"}])
    assert r.status_code == 201, r.content


def test_vat_option(cashier, para):
    s = ShopSettings.load()
    s.vat_enabled = True
    s.vat_rate = Decimal("10")
    s.save()
    r = checkout(cashier, [{"product_unit": para.u_strip.id, "qty": 2}],
                 [{"method": "cash_usd", "amount": "5.50"}])
    assert r.status_code == 201, r.content
    assert Decimal(r.json()["vat_amount"]) == Decimal("0.50")
    assert Decimal(r.json()["total"]) == Decimal("5.50")


def test_void_returns_stock_to_same_batches(cashier, para, branch):
    r = checkout(cashier, [{"product_unit": para.u_strip.id, "qty": 2}],
                 [{"method": "cash_usd", "amount": "5"}])
    sale_id = r.json()["id"]
    assert cashier.post(f"/api/sales/{sale_id}/void/", {"reason": "x"}).status_code == 403

    manager = client_for(User.Role.MANAGER, branch)
    r = manager.post(f"/api/sales/{sale_id}/void/", {"reason": "Customer changed mind"})
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "voided"
    assert StockBatch.objects.get(batch_no="EARLY").qty_on_hand == 15
    assert StockBatch.objects.get(batch_no="LATE").qty_on_hand == 100


def test_pos_catalog_lists_units_prices_and_sellable_stock(cashier, para, branch):
    receive_stock(product=para, branch=branch, batch_no="OLD", expiry_date=TODAY - timedelta(days=1),
                  unit_cost=Decimal("0.1"), qty=999)
    r = cashier.get("/api/pos/catalog/")
    assert r.status_code == 200
    item = next(p for p in r.json()["products"] if p["sku"] == "PARA")
    assert item["stock"] == 115  # expired batch not counted
    strip = next(u for u in item["units"] if u["unit"] == "Strip")
    assert strip["barcode"] == "PARAS"
    assert strip["prices"] == [{"min_qty": 1, "price": "2.50"}, {"min_qty": 5, "price": "2.20"}]


def test_user_without_branch_cannot_sell(para):
    user = User.objects.create_user("nobranch", password="pass-1234-xyz")
    c = APIClient()
    c.force_authenticate(user)
    r = checkout(c, [{"product_unit": para.u_tab.id, "qty": 1}],
                 [{"method": "cash_usd", "amount": "1"}])
    assert r.status_code == 400


def test_only_manager_changes_rate_and_settings(cashier, branch):
    assert cashier.post("/api/exchange-rates/", {"khr_per_usd": "4050"}).status_code == 403
    assert cashier.patch("/api/shop-settings/", {"vat_enabled": True}, format="json").status_code == 403
    manager = client_for(User.Role.MANAGER, branch)
    assert manager.post("/api/exchange-rates/", {"khr_per_usd": "4050"}).status_code == 201
    assert ExchangeRate.current() == Decimal("4050")
    r = manager.patch("/api/shop-settings/", {"receipt_width": "58"}, format="json")
    assert r.status_code == 200 and r.json()["receipt_width"] == "58"


def test_sale_with_prescription_photo_multipart(cashier, para, tmp_path, settings):
    import json

    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    body = {"client_uuid": str(uuid.uuid4()),
            "lines": [{"product_unit": para.u_tab.id, "qty": 1}],
            "payments": [{"method": "cash_usd", "amount": "1"}]}
    photo = SimpleUploadedFile("rx.jpg", b"fake-image", content_type="image/jpeg")
    r = cashier.post("/api/sales/", {"data": json.dumps(body), "prescription_image": photo},
                     format="multipart")
    assert r.status_code == 201, r.content
    assert Sale.objects.get().prescription_image.name.startswith("prescriptions/")
