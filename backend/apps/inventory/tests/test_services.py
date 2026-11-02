from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import Branch
from apps.catalog.models import Product
from apps.inventory import services
from apps.inventory.models import StockMovement

TODAY = date(2026, 11, 2)


@pytest.fixture
def branch(db):
    return Branch.objects.create(code="PP1", name="Phnom Penh 1")


@pytest.fixture
def product(db):
    return Product.objects.create(
        sku="PARA500", generic_name="Paracetamol", strength="500 mg", dosage_form="tablet"
    )


def receive(product, branch, batch_no, expiry, qty, cost="0.05"):
    return services.receive_stock(
        product=product, branch=branch, batch_no=batch_no,
        expiry_date=expiry, unit_cost=Decimal(cost), qty=qty,
    )


def test_receive_adds_stock_and_logs_movement(product, branch):
    batch = receive(product, branch, "A1", date(2027, 6, 1), 100)
    assert batch.qty_on_hand == 100
    mv = StockMovement.objects.get(batch=batch)
    assert mv.kind == StockMovement.Kind.RECEIPT and mv.qty == 100


def test_fefo_takes_earliest_expiry_first(product, branch):
    late = receive(product, branch, "LATE", date(2027, 12, 1), 50)
    early = receive(product, branch, "EARLY", date(2027, 1, 1), 30)

    allocs = services.issue_stock_fefo(product=product, branch=branch, qty=40, on_date=TODAY)

    assert [(a.batch.batch_no, a.qty) for a in allocs] == [("EARLY", 30), ("LATE", 10)]
    early.refresh_from_db()
    late.refresh_from_db()
    assert early.qty_on_hand == 0 and late.qty_on_hand == 40


def test_expired_batches_are_never_sold(product, branch):
    receive(product, branch, "OLD", date(2026, 10, 1), 100)
    receive(product, branch, "NEW", date(2027, 10, 1), 5)

    assert services.sellable_qty(product, branch, on_date=TODAY) == 5
    with pytest.raises(services.InsufficientStock):
        services.issue_stock_fefo(product=product, branch=branch, qty=6, on_date=TODAY)


def test_failed_issue_changes_nothing(product, branch):
    batch = receive(product, branch, "A1", date(2027, 6, 1), 10)
    with pytest.raises(services.InsufficientStock):
        services.issue_stock_fefo(product=product, branch=branch, qty=11, on_date=TODAY)
    batch.refresh_from_db()
    assert batch.qty_on_hand == 10
    assert StockMovement.objects.filter(kind=StockMovement.Kind.SALE).count() == 0


def test_adjust_logs_difference(product, branch):
    batch = receive(product, branch, "A1", date(2027, 6, 1), 10)
    services.adjust_stock(batch=batch, new_qty=7, note="count")
    mv = StockMovement.objects.get(kind=StockMovement.Kind.ADJUSTMENT)
    assert mv.qty == -3


def test_receiving_known_batch_with_other_expiry_fails(product, branch):
    receive(product, branch, "A1", date(2027, 6, 1), 10)
    with pytest.raises(services.BatchMismatch):
        receive(product, branch, "A1", date(2027, 7, 1), 10)
