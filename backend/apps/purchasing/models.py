"""Suppliers, purchase orders and goods receipts.

Quantities on order and receipt lines are entered in the unit the supplier
uses (box, strip, tablet). Each line also stores the same quantity in base
units, because stock is always kept in base units.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Branch
from apps.catalog.models import Product, ProductUnit
from apps.inventory.models import StockBatch


class Supplier(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200, db_index=True)
    contact_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField("VAT / tax ID", max_length=40, blank=True)
    payment_terms_days = models.PositiveIntegerField(
        default=0, help_text="Days of credit; 0 means cash on delivery"
    )
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class NumberedDocument(models.Model):
    """Gives each document a readable number such as PO-202611-00012."""

    PREFIX = ""

    number = models.CharField(max_length=30, unique=True, editable=False, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            stamp = (self.created_at or timezone.now()).strftime("%Y%m")
            self.number = f"{self.PREFIX}-{stamp}-{self.pk:05d}"
            type(self).objects.filter(pk=self.pk).update(number=self.number)


class PurchaseOrder(NumberedDocument):
    PREFIX = "PO"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ORDERED = "ordered", "Ordered"
        PARTIAL = "partial", "Partially received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="orders")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    order_date = models.DateField(default=timezone.localdate)
    expected_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.number or f"PO #{self.pk}"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), Decimal("0"))

    @property
    def is_receivable(self):
        return self.status in (self.Status.ORDERED, self.Status.PARTIAL)

    def refresh_status(self):
        """Set ordered / partial / received from what has been received."""
        if not self.is_receivable:
            return
        lines = list(self.lines.all())
        received_any = any(line.received_base_qty > 0 for line in lines)
        all_done = lines and all(line.remaining_base_qty == 0 for line in lines)
        if all_done:
            self.status = self.Status.RECEIVED
        elif received_any:
            self.status = self.Status.PARTIAL
        else:
            self.status = self.Status.ORDERED
        self.save(update_fields=["status", "updated_at"])


class PurchaseOrderLine(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_unit = models.ForeignKey(
        ProductUnit, on_delete=models.PROTECT, help_text="Unit ordered, e.g. Box"
    )
    qty = models.PositiveIntegerField(help_text="Quantity in the ordered unit")
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=4, help_text="Price per ordered unit"
    )
    received_base_qty = models.PositiveIntegerField(
        default=0, help_text="Base units received so far"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.order}: {self.qty} x {self.product_unit}"

    @property
    def base_qty(self):
        return self.qty * self.product_unit.factor

    @property
    def remaining_base_qty(self):
        return max(self.base_qty - self.received_base_qty, 0)

    @property
    def line_total(self):
        return self.qty * self.unit_price


class GoodsReceipt(NumberedDocument):
    """Goods received from a supplier. Saving it puts the stock into batches.

    A receipt is posted once and never edited; mistakes are fixed with a
    stock adjustment or a return to supplier.
    """

    PREFIX = "GRN"

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="receipts")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="goods_receipts")
    purchase_order = models.ForeignKey(
        PurchaseOrder, null=True, blank=True, on_delete=models.PROTECT, related_name="receipts"
    )
    received_date = models.DateField(default=timezone.localdate)
    supplier_invoice_no = models.CharField(max_length=60, blank=True)
    note = models.TextField(blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.number or f"GRN #{self.pk}"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), Decimal("0"))


class GoodsReceiptLine(models.Model):
    receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="lines")
    order_line = models.ForeignKey(
        PurchaseOrderLine, null=True, blank=True, on_delete=models.PROTECT,
        related_name="receipt_lines",
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_unit = models.ForeignKey(ProductUnit, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(help_text="Quantity in the received unit")
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=4, help_text="Cost per received unit"
    )
    batch_no = models.CharField(max_length=60)
    expiry_date = models.DateField()
    base_qty = models.PositiveIntegerField(help_text="Quantity in base units")
    base_unit_cost = models.DecimalField(
        max_digits=12, decimal_places=4, help_text="Cost per base unit"
    )
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="receipt_lines")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.receipt}: {self.qty} x {self.product_unit} #{self.batch_no}"

    @property
    def line_total(self):
        return self.qty * self.unit_cost
