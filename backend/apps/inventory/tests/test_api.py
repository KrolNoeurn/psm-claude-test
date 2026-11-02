import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Branch, User
from apps.catalog.models import Product


@pytest.fixture
def client(db):
    user = User.objects.create_user("cashier", password="pass-1234-xyz")
    c = APIClient()
    token = c.post(
        "/api/auth/token/", {"username": "cashier", "password": "pass-1234-xyz"}
    ).json()["access"]
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    c.user = user
    return c


def test_api_requires_login(db):
    assert APIClient().get("/api/products/").status_code == 401


def test_receive_then_list_batches(client):
    branch = Branch.objects.create(code="PP1", name="Phnom Penh 1")
    product = Product.objects.create(sku="AMOX", generic_name="Amoxicillin", dosage_form="capsule")
    r = client.post("/api/stock/batches/receive/", {
        "product": product.id, "branch": branch.id, "batch_no": "B1",
        "expiry_date": "2027-05-01", "unit_cost": "0.10", "qty": 200,
    }, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["qty_on_hand"] == 200

    listed = client.get("/api/stock/batches/", {"product": product.id}).json()
    assert listed["count"] == 1

    me = client.get("/api/auth/me/").json()
    assert me["username"] == "cashier"
