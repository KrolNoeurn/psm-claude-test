import pytest

from apps.inventory.models import StockBatch, StockMovement
from apps.purchasing.models import PurchaseOrder


def create_po(client, supplier, branch, product):
    return client.post("/api/purchase-orders/", {
        "supplier": supplier.id, "branch": branch.id, "expected_date": "2026-11-10",
        "lines": [{"product": product.id, "product_unit": product.u_box.id,
                   "qty": 5, "unit_price": "12.00"}],
    }, format="json")


def test_full_purchasing_flow(stock_client, supplier, branch, product):
    r = create_po(stock_client, supplier, branch, product)
    assert r.status_code == 201, r.content
    po = r.json()
    assert po["status"] == "draft" and po["number"].startswith("PO-")
    assert po["total"] == "60.0000" and po["lines"][0]["base_qty"] == 500

    r = stock_client.post(f"/api/purchase-orders/{po['id']}/submit/")
    assert r.status_code == 200 and r.json()["status"] == "ordered"

    line_id = po["lines"][0]["id"]
    r = stock_client.post("/api/goods-receipts/", {
        "supplier": supplier.id, "branch": branch.id, "purchase_order": po["id"],
        "supplier_invoice_no": "INV-88",
        "lines": [{"order_line": line_id, "product_unit": product.u_box.id, "qty": 5,
                   "unit_cost": "12.00", "batch_no": "LOT9", "expiry_date": "2028-01-31"}],
    }, format="json")
    assert r.status_code == 201, r.content
    grn = r.json()
    assert grn["lines"][0]["base_qty"] == 500
    assert grn["purchase_order_number"] == po["number"]

    assert StockBatch.objects.get(batch_no="LOT9").qty_on_hand == 500
    assert StockMovement.objects.filter(ref_id=grn["number"]).count() == 1
    assert stock_client.get(f"/api/purchase-orders/{po['id']}/").json()["status"] == "received"


def test_rule_errors_are_400_with_message(stock_client, supplier, branch, product):
    po = create_po(stock_client, supplier, branch, product).json()
    stock_client.post(f"/api/purchase-orders/{po['id']}/submit/")
    r = stock_client.post("/api/goods-receipts/", {
        "supplier": supplier.id, "branch": branch.id, "purchase_order": po["id"],
        "lines": [{"order_line": po["lines"][0]["id"], "product_unit": product.u_box.id,
                   "qty": 6, "unit_cost": "12", "batch_no": "X", "expiry_date": "2028-01-31"}],
    }, format="json")
    assert r.status_code == 400
    assert "still on order" in r.json()["detail"]


def test_only_draft_can_be_edited_or_deleted(stock_client, supplier, branch, product):
    po = create_po(stock_client, supplier, branch, product).json()
    r = stock_client.patch(f"/api/purchase-orders/{po['id']}/", {"lines": [
        {"product": product.id, "product_unit": product.u_strip.id, "qty": 20,
         "unit_price": "1.25"},
    ]}, format="json")
    assert r.status_code == 200 and r.json()["lines"][0]["base_qty"] == 200

    stock_client.post(f"/api/purchase-orders/{po['id']}/submit/")
    assert stock_client.patch(f"/api/purchase-orders/{po['id']}/", {"note": "x"},
                              format="json").status_code == 400
    assert stock_client.delete(f"/api/purchase-orders/{po['id']}/").status_code == 400
    r = stock_client.post(f"/api/purchase-orders/{po['id']}/cancel/")
    assert r.json()["status"] == PurchaseOrder.Status.CANCELLED


def test_wrong_unit_for_product_is_rejected(stock_client, supplier, branch, product):
    from apps.catalog.models import Product, ProductUnit, Unit
    other = Product.objects.create(sku="O", generic_name="Other", dosage_form="tablet")
    wrong = ProductUnit.objects.create(product=other, unit=Unit.objects.create(name="Vial"),
                                       factor=1, is_base=True)
    r = stock_client.post("/api/purchase-orders/", {
        "supplier": supplier.id, "branch": branch.id,
        "lines": [{"product": product.id, "product_unit": wrong.id, "qty": 1, "unit_price": "1"}],
    }, format="json")
    assert r.status_code == 400


def test_cashier_can_read_but_not_buy(cashier_client, supplier, branch, product):
    assert cashier_client.get("/api/suppliers/").status_code == 200
    assert create_po(cashier_client, supplier, branch, product).status_code == 403
    assert cashier_client.post("/api/suppliers/", {"code": "S2", "name": "X"}).status_code == 403


@pytest.mark.parametrize("path", ["/api/suppliers/", "/api/purchase-orders/",
                                  "/api/goods-receipts/"])
def test_login_required(db, path):
    from rest_framework.test import APIClient
    assert APIClient().get(path).status_code == 401


def test_supplier_with_documents_cannot_be_deleted(stock_client, supplier, branch, product):
    create_po(stock_client, supplier, branch, product)
    assert stock_client.delete(f"/api/suppliers/{supplier.id}/").status_code == 400
