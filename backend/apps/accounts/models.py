from django.contrib.auth.models import AbstractUser
from django.db import models


class Branch(models.Model):
    """A shop or warehouse. Stock, sales and users belong to a branch."""

    class Kind(models.TextChoices):
        RETAIL = "retail", "Retail shop"
        WAREHOUSE = "warehouse", "Wholesale warehouse"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.RETAIL)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "branches"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class User(AbstractUser):
    """Staff user. Permissions come from Django Groups (one group per role)."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Owner / Admin"
        MANAGER = "manager", "Manager"
        PHARMACIST = "pharmacist", "Pharmacist"
        CASHIER = "cashier", "Cashier"
        WHOLESALE = "wholesale", "Wholesale sales"
        STOCK = "stock", "Stock keeper"
        ACCOUNTANT = "accountant", "Accountant"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)
    branch = models.ForeignKey(
        Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="users"
    )
    phone = models.CharField(max_length=40, blank=True)
