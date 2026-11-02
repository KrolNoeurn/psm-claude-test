"""Retail sale rules: pricing, checkout with FEFO stock, payments and voids."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import ProductPrice
from apps.inventory import services as stock
from apps.inventory.models import StockMovement

from .models import ExchangeRate, Payment, Sale, SaleItem, SaleItemBatch, ShopSettings

CENT = Decimal("0.01")
RETAIL_TIER = "RETAIL"
APPROVER_ROLES = {User.Role.ADMIN, User.Role.MANAGER, User.Role.PHARMACIST}
VOID_ROLES = {User.Role.ADMIN, User.Role.MANAGER}


class SaleError(Exception):
    """A sale cannot be completed; the message is shown to the cashier."""

    def __init__(self, message, code="invalid"):
        super().__init__(message)
        self.code = code


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def retail_price(product_unit, qty):
    """Retail price for `qty` of a unit: the highest quantity break reached."""
    price = (
        ProductPrice.objects.filter(
            product_unit=product_unit, tier__code=RETAIL_TIER, min_qty__lte=qty
        )
        .order_by("-min_qty")
        .first()
    )
    if price is None:
        raise SaleError(f"{product_unit} has no retail price", code="no_price")
    return price.price


def can_approve(user):
    return bool(user) and (user.is_superuser or user.role in APPROVER_ROLES)


@dataclass
class LineInput:
    product_unit: object
    qty: int
    discount: Decimal = Decimal("0")


@dataclass
class PaymentInput:
    method: str
    amount: Decimal
    reference: str = ""


@dataclass
class SaleInput:
    client_uuid: object
    branch: object
    cashier: object
    lines: list
    payments: list
    discount: Decimal = Decimal("0")
    approver: object = None
    sold_at: object = None
    customer_name: str = ""
    customer_phone: str = ""
    note: str = ""
    prescription_image: object = None


def next_number(branch):
    """Daily running number per branch, e.g. PP1-261102-0007."""
    prefix = f"{branch.code}-{timezone.localdate():%y%m%d}-"
    last = (
        Sale.objects.select_for_update()
        .filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


@transaction.atomic
def create_sale(data: SaleInput):
    """Create a retail sale, take stock by FEFO and record payments.

    Saving the same `client_uuid` twice returns the first sale, so the POS
    can safely resend sales that were queued while offline.
    """
    existing = Sale.objects.filter(client_uuid=data.client_uuid).first()
    if existing:
        return existing, False

    if not data.lines:
        raise SaleError("The cart is empty", code="empty")

    controlled = [l for l in data.lines if l.product_unit.product.is_controlled]
    approver = None
    if controlled:
        approver = data.cashier if can_approve(data.cashier) else data.approver
        if not can_approve(approver):
            names = ", ".join(str(l.product_unit.product) for l in controlled)
            raise SaleError(
                f"A pharmacist must approve controlled drugs: {names}", code="approval_required"
            )

    shop = ShopSettings.load()
    rate = ExchangeRate.current()
    sale = Sale(
        number=next_number(data.branch),
        client_uuid=data.client_uuid,
        sale_type=Sale.Type.RETAIL,
        branch=data.branch,
        cashier=data.cashier,
        approved_by=approver,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        note=data.note,
        exchange_rate=rate,
        sold_at=data.sold_at or timezone.now(),
        subtotal=0, total=0, paid=0,
    )
    if data.prescription_image:
        sale.prescription_image = data.prescription_image
    sale.save()

    subtotal = Decimal("0")
    for line in data.lines:
        if line.qty <= 0:
            raise SaleError("Quantity must be at least 1")
        pu = line.product_unit
        unit_price = retail_price(pu, line.qty)
        line_discount = money(line.discount or 0)
        gross = money(unit_price * line.qty)
        if line_discount < 0 or line_discount > gross:
            raise SaleError(f"Invalid discount on {pu}")
        base_qty = pu.to_base(line.qty)
        try:
            allocations = stock.issue_stock_fefo(
                product=pu.product, branch=data.branch, qty=base_qty,
                kind=StockMovement.Kind.SALE, user=data.cashier,
                ref_type="sale", ref_id=sale.number,
            )
        except stock.InsufficientStock:
            available = stock.sellable_qty(pu.product, data.branch)
            raise SaleError(
                f"Not enough stock for {pu.product}: need {base_qty}, have {available} "
                f"(base units)", code="insufficient_stock",
            )
        cost = sum((a.batch.unit_cost * a.qty for a in allocations), Decimal("0"))
        item = SaleItem.objects.create(
            sale=sale, product_unit=pu, qty=line.qty, base_qty=base_qty,
            unit_price=unit_price, discount=line_discount,
            line_total=gross - line_discount, cost=cost,
        )
        SaleItemBatch.objects.bulk_create(
            SaleItemBatch(item=item, batch=a.batch, qty=a.qty, unit_cost=a.batch.unit_cost)
            for a in allocations
        )
        subtotal += item.line_total

    discount = money(data.discount or 0)
    if discount < 0 or discount > subtotal:
        raise SaleError("Invalid sale discount")
    taxable = subtotal - discount
    vat_rate = shop.vat_rate if shop.vat_enabled else Decimal("0")
    vat_amount = money(taxable * vat_rate / 100)
    total = taxable + vat_amount

    paid = Decimal("0")
    for p in data.payments:
        amount = Decimal(p.amount)
        if amount <= 0:
            raise SaleError("Payment amounts must be positive")
        if p.method == Payment.Method.CASH_KHR:
            currency, amount_usd = "KHR", money(amount / rate)
        elif p.method in (Payment.Method.CASH_USD, Payment.Method.KHQR):
            currency, amount_usd = "USD", money(amount)
        else:
            raise SaleError(f"Unknown payment method {p.method}")
        Payment.objects.create(
            sale=sale, method=p.method, amount=amount, currency=currency,
            amount_usd=amount_usd, reference=p.reference,
        )
        paid += amount_usd

    # A riel payment rounded to 100 riel can fall a few cents short of the dollar total.
    tolerance = money(Decimal("100") / rate)
    if paid + tolerance < total:
        raise SaleError(f"Paid {paid} USD but the total is {total} USD", code="underpaid")

    sale.subtotal = subtotal
    sale.discount = discount
    sale.vat_rate = vat_rate
    sale.vat_amount = vat_amount
    sale.total = total
    sale.paid = paid
    sale.change_usd = max(paid - total, Decimal("0"))
    sale.save()
    return sale, True


@transaction.atomic
def void_sale(*, sale, user, reason):
    """Cancel a sale and put its stock back into the same batches."""
    if not (user.is_superuser or user.role in VOID_ROLES):
        raise SaleError("Only a manager can void a sale", code="forbidden")
    sale = Sale.objects.select_for_update().get(pk=sale.pk)
    if sale.status == Sale.Status.VOIDED:
        raise SaleError("This sale is already voided")
    for item in sale.items.prefetch_related("batches__batch"):
        for ib in item.batches.all():
            batch = type(ib.batch).objects.select_for_update().get(pk=ib.batch_id)
            batch.qty_on_hand += ib.qty
            batch.save(update_fields=["qty_on_hand"])
            StockMovement.objects.create(
                batch=batch, kind=StockMovement.Kind.SALE_RETURN, qty=ib.qty,
                user=user, ref_type="sale_void", ref_id=sale.number, note=reason,
            )
    sale.status = Sale.Status.VOIDED
    sale.voided_at = timezone.now()
    sale.voided_by = user
    sale.void_reason = reason
    sale.save(update_fields=["status", "voided_at", "voided_by", "void_reason"])
    return sale


def pos_catalog(branch):
    """Everything the POS needs to sell offline: units, barcodes, prices, stock."""
    from django.db.models import Sum

    from apps.catalog.models import Product
    from apps.inventory.models import StockBatch

    today = timezone.localdate()
    stock_by_product = dict(
        StockBatch.objects.filter(branch=branch, expiry_date__gt=today, qty_on_hand__gt=0)
        .values("product").annotate(total=Sum("qty_on_hand")).values_list("product", "total")
    )
    products = (
        Product.objects.filter(is_active=True)
        .prefetch_related("units__unit", "units__prices__tier")
        .order_by("generic_name")
    )
    result = []
    for p in products:
        units = []
        for u in p.units.all():
            prices = sorted(
                ({"min_qty": pr.min_qty, "price": str(pr.price)}
                 for pr in u.prices.all() if pr.tier.code == RETAIL_TIER),
                key=lambda x: x["min_qty"],
            )
            units.append({
                "id": u.id, "unit": u.unit.name, "unit_km": u.unit.name_km,
                "factor": u.factor, "barcode": u.barcode, "is_base": u.is_base,
                "prices": prices,
            })
        result.append({
            "id": p.id, "sku": p.sku, "name": str(p), "generic_name": p.generic_name,
            "brand_name": p.brand_name, "strength": p.strength,
            "is_prescription_required": p.is_prescription_required,
            "is_controlled": p.is_controlled,
            "stock": stock_by_product.get(p.id, 0),
            "units": units,
        })
    return result
