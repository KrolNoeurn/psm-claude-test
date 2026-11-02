from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    name = models.CharField(max_length=120, unique=True)
    country = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Unit(models.Model):
    """A packaging unit such as tablet, strip, box or carton."""

    name = models.CharField(max_length=40, unique=True)
    name_km = models.CharField("Khmer name", max_length=40, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    class DosageForm(models.TextChoices):
        TABLET = "tablet", "Tablet"
        CAPSULE = "capsule", "Capsule"
        SYRUP = "syrup", "Syrup"
        INJECTION = "injection", "Injection"
        CREAM = "cream", "Cream / Ointment"
        DROPS = "drops", "Drops"
        OTHER = "other", "Other"

    sku = models.CharField(max_length=40, unique=True)
    generic_name = models.CharField(max_length=200, db_index=True)
    brand_name = models.CharField(max_length=200, blank=True, db_index=True)
    dosage_form = models.CharField(max_length=20, choices=DosageForm.choices)
    strength = models.CharField(max_length=60, blank=True, help_text="e.g. 500 mg")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT)
    manufacturer = models.ForeignKey(
        Manufacturer, null=True, blank=True, on_delete=models.PROTECT
    )
    is_prescription_required = models.BooleanField(default=False)
    is_controlled = models.BooleanField(default=False)
    reorder_level = models.PositiveIntegerField(
        default=0, help_text="Alert when stock (in base units) falls to this level"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["generic_name"]

    def __str__(self):
        label = self.brand_name or self.generic_name
        return f"{label} {self.strength}".strip()

    @property
    def base_unit(self):
        return self.units.filter(is_base=True).first()


class ProductUnit(models.Model):
    """How a product is sold in a unit, e.g. 1 box = 100 tablets.

    All stock quantities are stored in the base unit (factor = 1);
    the factor converts a sale or purchase quantity into base units.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="units")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    factor = models.PositiveIntegerField(help_text="Number of base units in this unit")
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    is_base = models.BooleanField(default=False)

    class Meta:
        ordering = ["product", "factor"]
        constraints = [
            models.UniqueConstraint(fields=["product", "unit"], name="uniq_product_unit"),
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_base=True),
                name="one_base_unit_per_product",
            ),
        ]

    def clean(self):
        if self.is_base and self.factor != 1:
            raise ValidationError({"factor": "The base unit must have factor 1."})

    def to_base(self, qty):
        return qty * self.factor

    def __str__(self):
        return f"{self.product} / {self.unit} (x{self.factor})"


class PriceTier(models.Model):
    """A price list, e.g. Retail, Wholesale A, Wholesale B."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    is_wholesale = models.BooleanField(default=False)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class ProductPrice(models.Model):
    product_unit = models.ForeignKey(
        ProductUnit, on_delete=models.CASCADE, related_name="prices"
    )
    tier = models.ForeignKey(PriceTier, on_delete=models.PROTECT, related_name="prices")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    min_qty = models.PositiveIntegerField(
        default=1, help_text="Minimum quantity (in this unit) for this price"
    )

    class Meta:
        ordering = ["product_unit", "tier", "min_qty"]
        constraints = [
            models.UniqueConstraint(
                fields=["product_unit", "tier", "min_qty"], name="uniq_price_break"
            )
        ]

    def __str__(self):
        return f"{self.product_unit} @ {self.tier}: {self.price}"
