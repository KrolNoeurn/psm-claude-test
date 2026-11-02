"""Load a small demo dataset: one branch, an admin user, units, price tiers,
two products with box/strip/tablet units, and a few stock batches."""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Branch, User
from apps.catalog.models import PriceTier, Product, ProductPrice, ProductUnit, Unit
from apps.inventory.services import receive_stock


class Command(BaseCommand):
    help = "Create demo data for local development"

    @transaction.atomic
    def handle(self, *args, **options):
        branch, _ = Branch.objects.get_or_create(code="PP1", defaults={"name": "Phnom Penh 1"})
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                "admin", password="admin12345", role=User.Role.ADMIN, branch=branch
            )

        tablet, _ = Unit.objects.get_or_create(name="Tablet", defaults={"name_km": "គ្រាប់"})
        strip, _ = Unit.objects.get_or_create(name="Strip", defaults={"name_km": "បន្ទះ"})
        box, _ = Unit.objects.get_or_create(name="Box", defaults={"name_km": "ប្រអប់"})
        retail, _ = PriceTier.objects.get_or_create(code="RETAIL", defaults={"name": "Retail"})
        whole, _ = PriceTier.objects.get_or_create(
            code="WS-A", defaults={"name": "Wholesale A", "is_wholesale": True}
        )

        today = timezone.localdate()
        demo = [
            ("PARA500", "Paracetamol", "Panadol", "500 mg", False, "0.30", "2.50", "22.00"),
            ("AMOX500", "Amoxicillin", "", "500 mg", True, "0.50", "4.50", "40.00"),
        ]
        for sku, generic, brand, strength, rx, tab_price, strip_price, box_ws in demo:
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults=dict(generic_name=generic, brand_name=brand, strength=strength,
                              dosage_form="tablet", is_prescription_required=rx,
                              reorder_level=200),
            )
            if not created:
                continue
            u_tab = ProductUnit.objects.create(product=product, unit=tablet, factor=1, is_base=True)
            u_strip = ProductUnit.objects.create(product=product, unit=strip, factor=10)
            u_box = ProductUnit.objects.create(product=product, unit=box, factor=100)
            ProductPrice.objects.create(product_unit=u_tab, tier=retail, price=Decimal(tab_price))
            ProductPrice.objects.create(product_unit=u_strip, tier=retail, price=Decimal(strip_price))
            ProductPrice.objects.create(product_unit=u_box, tier=whole, price=Decimal(box_ws))
            receive_stock(product=product, branch=branch, batch_no=f"{sku}-A",
                          expiry_date=today + timedelta(days=45), unit_cost=Decimal("0.15"), qty=300)
            receive_stock(product=product, branch=branch, batch_no=f"{sku}-B",
                          expiry_date=today + timedelta(days=400), unit_cost=Decimal("0.14"), qty=1000)

        self.stdout.write(self.style.SUCCESS("Demo data ready. Login: admin / admin12345"))
