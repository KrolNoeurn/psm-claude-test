"""Purchasing business rules: PO status changes and posting goods receipts.

Posting a goods receipt is the only way purchasing changes stock. It runs in
one transaction: every line becomes (or tops up) a StockBatch through
`apps.inventory.services.receive_stock`, which writes the StockMovement
ledger row. If any line is invalid, nothing is saved.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import StockMovement
from apps.inventory.services import BatchMismatch, receive_stock

from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine


class PurchasingError(ValueError):
    """A purchasing rule was broken. The message is safe to show to users."""


@dataclass
class ReceiptLineInput:
    product: object
    product_unit: object
    qty: int
    unit_cost: Decimal
    batch_no: str
    expiry_date: date
    order_line: PurchaseOrderLine | None = None


def _lock_order(order):
    return PurchaseOrder.objects.select_for_update().get(pk=order.pk)


@transaction.atomic
def submit_order(order):
    """Draft -> Ordered (sent to the supplier). Lines can no longer change."""
    order = _lock_order(order)
    if order.status != PurchaseOrder.Status.DRAFT:
        raise PurchasingError("Only a draft purchase order can be submitted.")
    if not order.lines.exists():
        raise PurchasingError("Add at least one line before submitting.")
    order.status = PurchaseOrder.Status.ORDERED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def cancel_order(order):
    """Cancel a PO that has not received any goods yet."""
    order = _lock_order(order)
    if order.status not in (PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.ORDERED):
        raise PurchasingError(
            "Only a draft or ordered purchase order with nothing received can be cancelled."
        )
    order.status = PurchaseOrder.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def close_order(order):
    """Close a partially received PO when the rest will not come."""
    order = _lock_order(order)
    if order.status != PurchaseOrder.Status.PARTIAL:
        raise PurchasingError("Only a partially received purchase order can be closed.")
    order.status = PurchaseOrder.Status.RECEIVED
    order.save(update_fields=["status", "updated_at"])
    return order


def _check_line(line: ReceiptLineInput, order, today):
    if line.product_unit.product_id != line.product.pk:
        raise PurchasingError(f"Unit {line.product_unit} does not belong to {line.product}.")
    if line.qty <= 0:
        raise PurchasingError("Quantity must be more than zero.")
    if line.unit_cost < 0:
        raise PurchasingError("Cost cannot be negative.")
    if not line.batch_no.strip():
        raise PurchasingError(f"Batch number is required for {line.product}.")
    if line.expiry_date <= today:
        raise PurchasingError(
            f"{line.product} batch {line.batch_no} is already expired ({line.expiry_date})."
        )
    if line.order_line is not None:
        if order is None or line.order_line.order_id != order.pk:
            raise PurchasingError("The order line does not belong to this purchase order.")
        if line.order_line.product_id != line.product.pk:
            raise PurchasingError(f"The order line is for another product, not {line.product}.")
    elif order is not None:
        raise PurchasingError(
            f"{line.product} must be linked to a line of {order}. "
            "Receive extra items on a separate receipt without a PO."
        )


@transaction.atomic
def post_goods_receipt(*, supplier, branch, lines, user=None, purchase_order=None,
                       received_date=None, supplier_invoice_no="", note="", today=None):
    """Create a goods receipt and put every line into stock.

    `lines` is a list of ReceiptLineInput. Quantities and costs are in the
    received unit; they are converted to base units for the stock batch.
    """
    today = today or timezone.localdate()
    if not lines:
        raise PurchasingError("A goods receipt needs at least one line.")

    order = None
    if purchase_order is not None:
        order = _lock_order(purchase_order)
        if not order.is_receivable:
            raise PurchasingError(f"{order} is {order.get_status_display().lower()}; "
                                  "it cannot receive goods.")
        if order.supplier_id != supplier.pk:
            raise PurchasingError(f"{order} is from another supplier.")
        if order.branch_id != branch.pk:
            raise PurchasingError(f"{order} is for another branch.")

    # Lock the order lines and check that we never receive more than ordered.
    order_lines = {}
    if order is not None:
        order_lines = {
            ol.pk: ol for ol in
            PurchaseOrderLine.objects.select_for_update().select_related("product_unit")
            .filter(order=order)
        }
    incoming = {}
    for line in lines:
        _check_line(line, order, today)
        if line.order_line is not None:
            line.order_line = order_lines[line.order_line.pk]
            key = line.order_line.pk
            incoming[key] = incoming.get(key, 0) + line.product_unit.to_base(line.qty)
    for key, base_qty in incoming.items():
        ol = order_lines[key]
        if base_qty > ol.remaining_base_qty:
            raise PurchasingError(
                f"{ol.product}: receiving {base_qty} base units but only "
                f"{ol.remaining_base_qty} are still on order."
            )

    receipt = GoodsReceipt.objects.create(
        supplier=supplier, branch=branch, purchase_order=order,
        received_date=received_date or today, supplier_invoice_no=supplier_invoice_no,
        note=note, received_by=user,
    )
    for line in lines:
        factor = line.product_unit.factor
        base_qty = line.qty * factor
        base_cost = (Decimal(line.unit_cost) / factor).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        try:
            batch = receive_stock(
                product=line.product, branch=branch, batch_no=line.batch_no.strip(),
                expiry_date=line.expiry_date, unit_cost=base_cost, qty=base_qty, user=user,
                ref_type="goods_receipt", ref_id=receipt.number,
            )
        except BatchMismatch as exc:
            raise PurchasingError(str(exc)) from exc
        GoodsReceiptLine.objects.create(
            receipt=receipt, order_line=line.order_line, product=line.product,
            product_unit=line.product_unit, qty=line.qty, unit_cost=line.unit_cost,
            batch_no=line.batch_no.strip(), expiry_date=line.expiry_date,
            base_qty=base_qty, base_unit_cost=base_cost, batch=batch,
        )
        if line.order_line is not None:
            line.order_line.received_base_qty += base_qty
            line.order_line.save(update_fields=["received_base_qty"])

    if order is not None:
        order.refresh_status()
    return receipt


def receipt_movements(receipt):
    """Ledger rows written by a goods receipt."""
    return StockMovement.objects.filter(
        kind=StockMovement.Kind.RECEIPT, ref_type="goods_receipt", ref_id=receipt.number
    )
