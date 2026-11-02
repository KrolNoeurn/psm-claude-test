"""Stock business rules. All stock changes go through these functions.

Every change runs in a database transaction, locks the affected batches
and writes a StockMovement row, so stock can be audited batch by batch.
"""

from dataclasses import dataclass
from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import StockBatch, StockMovement


class InsufficientStock(Exception):
    """Raised when there is not enough sellable (unexpired) stock."""


@dataclass
class Allocation:
    batch: StockBatch
    qty: int  # base units taken from this batch


@transaction.atomic
def receive_stock(*, product, branch, batch_no, expiry_date, unit_cost, qty,
                  user=None, ref_type="", ref_id=""):
    """Add `qty` base units of a batch to a branch (goods receipt)."""
    if qty <= 0:
        raise ValueError("qty must be positive")
    batch, _ = StockBatch.objects.select_for_update().get_or_create(
        product=product,
        branch=branch,
        batch_no=batch_no,
        defaults={"expiry_date": expiry_date, "unit_cost": unit_cost},
    )
    batch.qty_on_hand += qty
    batch.save(update_fields=["qty_on_hand"])
    StockMovement.objects.create(
        batch=batch, kind=StockMovement.Kind.RECEIPT, qty=qty,
        user=user, ref_type=ref_type, ref_id=str(ref_id),
    )
    return batch


def sellable_qty(product, branch, on_date=None):
    """Unexpired base units of a product available in a branch."""
    on_date = on_date or timezone.localdate()
    total = (
        StockBatch.objects.filter(
            product=product, branch=branch, expiry_date__gt=on_date, qty_on_hand__gt=0
        ).aggregate(total=Sum("qty_on_hand"))["total"]
    )
    return total or 0


@transaction.atomic
def issue_stock_fefo(*, product, branch, qty, kind=StockMovement.Kind.SALE,
                     user=None, ref_type="", ref_id="", on_date: date | None = None):
    """Take `qty` base units using FEFO (First Expiry, First Out).

    Expired batches are never issued. Returns the list of allocations so
    the caller can store the batch and cost on each sale line.
    """
    if qty <= 0:
        raise ValueError("qty must be positive")
    on_date = on_date or timezone.localdate()
    batches = (
        StockBatch.objects.select_for_update()
        .filter(product=product, branch=branch, expiry_date__gt=on_date, qty_on_hand__gt=0)
        .order_by("expiry_date", "id")
    )
    remaining = qty
    allocations = []
    for batch in batches:
        if remaining == 0:
            break
        take = min(batch.qty_on_hand, remaining)
        allocations.append(Allocation(batch=batch, qty=take))
        remaining -= take
    if remaining > 0:
        raise InsufficientStock(
            f"Need {qty} of {product}, only {qty - remaining} sellable in {branch}"
        )
    for alloc in allocations:
        alloc.batch.qty_on_hand -= alloc.qty
        alloc.batch.save(update_fields=["qty_on_hand"])
        StockMovement.objects.create(
            batch=alloc.batch, kind=kind, qty=-alloc.qty,
            user=user, ref_type=ref_type, ref_id=str(ref_id),
        )
    return allocations


@transaction.atomic
def adjust_stock(*, batch, new_qty, user=None, note=""):
    """Set a batch to a counted quantity (stock count) and log the difference."""
    if new_qty < 0:
        raise ValueError("new_qty cannot be negative")
    batch = StockBatch.objects.select_for_update().get(pk=batch.pk)
    diff = new_qty - batch.qty_on_hand
    if diff == 0:
        return batch
    batch.qty_on_hand = new_qty
    batch.save(update_fields=["qty_on_hand"])
    StockMovement.objects.create(
        batch=batch, kind=StockMovement.Kind.ADJUSTMENT, qty=diff, user=user, note=note
    )
    return batch
