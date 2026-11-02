from datetime import date
from decimal import Decimal

import pytest

from apps.inventory.models import StockBatch, StockMovement
from apps.purchasing import services
from apps.purchasing.models import GoodsReceipt, PurchaseOrder, PurchaseOrderLine
from apps.purchasing.services import PurchasingError, ReceiptLineInput

TODAY = date(2026, 11, 2)
EXPIRY = date(2028, 3, 31)


@pytest.fixture
def order(supplier, branch, product):
    po = PurchaseOrder.objects.create(supplier=supplier, branch=branch)
    PurchaseOrderLine.objects.create(
        order=po, product=product, product_unit=product.u_box, qty=5, unit_price=Decimal("12.00")
    )
    return services.submit_order(po)


def line_for(order, unit, qty, batch="LOT1", cost="12.00", expiry=EXPIRY):
    ol = order.lines.get()
    return ReceiptLineInput(
        product=ol.product, product_unit=unit, qty=qty, unit_cost=Decimal(cost),
        batch_no=batch, expiry_date=expiry, order_line=ol,
    )


def post(order, lines):
    return services.post_goods_receipt(
        supplier=order.supplier, branch=order.branch, purchase_order=order,
        lines=lines, today=TODAY,
    )


def test_numbers_are_readable(order):
    assert order.number.startswith("PO-") and order.number.endswith(f"{order.pk:05d}")
    assert order.status == PurchaseOrder.Status.ORDERED


def test_receipt_converts_boxes_to_base_units_and_writes_ledger(order, product):
    receipt = post(order, [line_for(order, product.u_box, 2, cost="12.00")])

    line = receipt.lines.get()
    assert line.base_qty == 200
    assert line.base_unit_cost == Decimal("0.1200")
    batch = StockBatch.objects.get(batch_no="LOT1")
    assert batch.qty_on_hand == 200 and batch.expiry_date == EXPIRY
    assert batch.unit_cost == Decimal("0.1200")

    mv = services.receipt_movements(receipt).get()
    assert mv.qty == 200 and mv.batch == batch and mv.ref_id == receipt.number
    assert receipt.number.startswith("GRN-")

    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.PARTIAL
    assert order.lines.get().remaining_base_qty == 300


def test_receiving_in_strips_completes_order(order, product):
    post(order, [line_for(order, product.u_box, 3)])
    post(order, [
        line_for(order, product.u_box, 1, batch="LOT2"),
        line_for(order, product.u_strip, 10, batch="LOT2", cost="1.20"),
    ])
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.RECEIVED
    assert StockBatch.objects.get(batch_no="LOT2").qty_on_hand == 200


def test_cannot_receive_more_than_ordered(order, product):
    with pytest.raises(PurchasingError, match="still on order"):
        post(order, [line_for(order, product.u_box, 4), line_for(order, product.u_strip, 11)])
    assert GoodsReceipt.objects.count() == 0
    assert StockMovement.objects.count() == 0


def test_expired_goods_are_rejected_and_nothing_is_saved(order, product):
    with pytest.raises(PurchasingError, match="expired"):
        post(order, [
            line_for(order, product.u_box, 1, batch="GOOD"),
            line_for(order, product.u_box, 1, batch="OLD", expiry=TODAY),
        ])
    assert not StockBatch.objects.exists()
    assert GoodsReceipt.objects.count() == 0


def test_same_batch_with_other_expiry_is_rejected(order, product):
    post(order, [line_for(order, product.u_box, 1)])
    with pytest.raises(PurchasingError, match="already exists"):
        post(order, [line_for(order, product.u_box, 1, expiry=date(2029, 1, 1))])
    assert StockBatch.objects.get().qty_on_hand == 100


def test_same_batch_again_averages_cost(order, product):
    post(order, [line_for(order, product.u_box, 1, cost="10.00")])
    post(order, [line_for(order, product.u_box, 1, cost="14.00")])
    batch = StockBatch.objects.get()
    assert batch.qty_on_hand == 200 and batch.unit_cost == Decimal("0.1200")


def test_unit_must_belong_to_product(order, product, db):
    from apps.catalog.models import Product, ProductUnit, Unit
    other = Product.objects.create(sku="X", generic_name="Other", dosage_form="tablet")
    wrong = ProductUnit.objects.create(product=other, unit=Unit.objects.create(name="Vial"),
                                       factor=1, is_base=True)
    with pytest.raises(PurchasingError, match="does not belong"):
        post(order, [line_for(order, wrong, 1)])


def test_draft_and_cancelled_orders_cannot_receive(supplier, branch, product, order):
    services.cancel_order(order)
    with pytest.raises(PurchasingError, match="cannot receive"):
        post(order, [line_for(order, product.u_box, 1)])


def test_cannot_cancel_after_receiving_but_can_close(order, product):
    post(order, [line_for(order, product.u_box, 1)])
    order.refresh_from_db()
    with pytest.raises(PurchasingError):
        services.cancel_order(order)
    assert services.close_order(order).status == PurchaseOrder.Status.RECEIVED


def test_direct_receipt_without_po(supplier, branch, product):
    receipt = services.post_goods_receipt(
        supplier=supplier, branch=branch, today=TODAY,
        lines=[ReceiptLineInput(product=product, product_unit=product.u_strip, qty=3,
                                unit_cost=Decimal("1.50"), batch_no="D1", expiry_date=EXPIRY)],
    )
    assert receipt.purchase_order is None
    assert StockBatch.objects.get(batch_no="D1").qty_on_hand == 30


def test_po_receipt_lines_must_link_to_order_line(order, product):
    loose = ReceiptLineInput(product=product, product_unit=product.u_box, qty=1,
                             unit_cost=Decimal("12"), batch_no="L", expiry_date=EXPIRY)
    with pytest.raises(PurchasingError, match="must be linked"):
        post(order, [loose])
