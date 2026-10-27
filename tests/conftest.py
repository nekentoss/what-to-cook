import pytest


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app

    application = create_app(tmp_path / "test.db")
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def products(client):
    return [
        client.post("/api/products", json={"name": name}).json()
        for name in ["Яйцо", "Молоко", "Сыр"]
    ]


@pytest.fixture
def recipe_payload(products):
    return {
        "name": "Омлет",
        "instructions": "Смешать и приготовить на сковороде.",
        "ingredient_ids": [products[0]["id"], products[1]["id"]],
    }
