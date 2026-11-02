"""Create the master data every shop needs: units, the Retail price tier,
shop settings and a starting exchange rate. Safe to run more than once."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.catalog.models import PriceTier, Unit
from apps.sales.models import ExchangeRate, ShopSettings

UNITS = [
    ("Tablet", "គ្រាប់"), ("Capsule", "គ្រាប់ capsule"), ("Strip", "បន្ទះ"),
    ("Blister", "សន្លឹក"), ("Box", "ប្រអប់"), ("Carton", "កេស"),
    ("Bottle", "ដប"), ("Tube", "បំពង់"), ("Ampoule", "អំពូល"), ("Vial", "ដបតូច"),
    ("Sachet", "កញ្ចប់"), ("Pack", "កញ្ចប់ធំ"), ("Piece", "ដុំ"), ("Pair", "គូ"),
    ("Roll", "ដុំរមូរ"), ("ml", "ml"), ("g", "g"),
]


class Command(BaseCommand):
    help = "Create default units, price tiers, shop settings and exchange rate"

    def handle(self, *args, **options):
        for name, km in UNITS:
            Unit.objects.get_or_create(name=name, defaults={"name_km": km})
        PriceTier.objects.get_or_create(code="RETAIL", defaults={"name": "Retail"})
        PriceTier.objects.get_or_create(
            code="WS-A", defaults={"name": "Wholesale A", "is_wholesale": True}
        )
        ShopSettings.load()
        if not ExchangeRate.objects.exists():
            ExchangeRate.objects.create(khr_per_usd=Decimal("4100"))
        self.stdout.write(self.style.SUCCESS(f"{len(UNITS)} units and shop defaults ready"))
