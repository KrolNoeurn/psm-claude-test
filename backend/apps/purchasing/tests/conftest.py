import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Branch, User
from apps.catalog.models import Product, ProductUnit, Unit
from apps.purchasing.models import Supplier


@pytest.fixture
def branch(db):
    return Branch.objects.create(code="PP1", name="Phnom Penh 1")


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(code="SUP1", name="Mekong Pharma")


@pytest.fixture
def product(db):
    """Paracetamol: 1 box = 10 strips = 100 tablets."""
    p = Product.objects.create(sku="PARA500", generic_name="Paracetamol", dosage_form="tablet")
    p.u_tab = ProductUnit.objects.create(
        product=p, unit=Unit.objects.create(name="Tablet"), factor=1, is_base=True)
    p.u_strip = ProductUnit.objects.create(
        product=p, unit=Unit.objects.create(name="Strip"), factor=10)
    p.u_box = ProductUnit.objects.create(
        product=p, unit=Unit.objects.create(name="Box"), factor=100)
    return p


def make_client(role):
    user = User.objects.create_user(f"u_{role}", password="pass-1234-xyz", role=role)
    c = APIClient()
    c.force_authenticate(user)
    c.user = user
    return c


@pytest.fixture
def stock_client(db):
    return make_client(User.Role.STOCK)


@pytest.fixture
def cashier_client(db):
    return make_client(User.Role.CASHIER)
