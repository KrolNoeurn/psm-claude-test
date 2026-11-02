from django.conf import settings
from django.db import models

from apps.accounts.models import Branch
from apps.catalog.models import Product


class StockBatch(models.Model):
    """One lot of a product in one branch, with its expiry date and cost.

    `qty_on_hand` is in base units and is only changed through
    `apps.inventory.services`, which also writes a StockMovement.
    """

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="batches")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="batches")
    batch_no = models.CharField(max_length=60)
    expiry_date = models.DateField(db_index=True)
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=4, help_text="Cost per base unit"
    )
    qty_on_hand = models.IntegerField(default=0)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expiry_date", "id"]
        verbose_name_plural = "stock batches"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "branch", "batch_no"], name="uniq_batch_per_branch"
            ),
            models.CheckConstraint(
                condition=models.Q(qty_on_hand__gte=0), name="batch_qty_not_negative"
            ),
        ]

    def __str__(self):
        return f"{self.product} #{self.batch_no} exp {self.expiry_date}"


class StockMovement(models.Model):
    """Append-only ledger of every stock change, in base units."""

    class Kind(models.TextChoices):
        RECEIPT = "receipt", "Goods receipt"
        SALE = "sale", "Sale"
        SALE_RETURN = "sale_return", "Customer return"
        PURCHASE_RETURN = "purchase_return", "Return to supplier"
        ADJUSTMENT = "adjustment", "Adjustment"
        TRANSFER_IN = "transfer_in", "Transfer in"
        TRANSFER_OUT = "transfer_out", "Transfer out"
        WRITE_OFF = "write_off", "Expired / damaged write-off"

    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    qty = models.IntegerField(help_text="Signed: positive adds stock, negative removes")
    ref_type = models.CharField(max_length=40, blank=True)
    ref_id = models.CharField(max_length=40, blank=True)
    note = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.kind} {self.qty:+d} on {self.batch}"
