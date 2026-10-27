import pytest


def test_seed_is_repeatable_and_preserves_user_data(client):
    from app.seed import seed_database

    milk = client.post("/api/products", json={"name": " молоко "}).json()
    avocado = client.post("/api/products", json={"name": "Авокадо"}).json()
    original = client.post("/api/recipes", json={
        "name": "Омлет", "instructions": "Мой собственный рецепт.",
        "ingredient_ids": [milk["id"], avocado["id"]],
    }).json()
    engine = client.app.state.engine
    assert seed_database(engine) == (14, 5)
    assert len(client.get("/api/products").json()) == 16
    assert len(client.get("/api/recipes").json()) == 6
    before = (client.get("/api/products").json(), client.get("/api/recipes").json())
    assert seed_database(engine) == (0, 0)
    assert before == (client.get("/api/products").json(), client.get("/api/recipes").json())
    assert client.get(f'/api/recipes/{original["id"]}').json() == original


def test_seed_empty_database(client):
    from app.seed import seed_database

    assert seed_database(client.app.state.engine) == (15, 6)
    assert seed_database(client.app.state.engine) == (0, 0)


def test_sqlite_enforces_foreign_keys(client):
    from sqlalchemy import insert, text
    from sqlalchemy.exc import IntegrityError
    from app.models import recipe_ingredients

    with client.app.state.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        connection.rollback()
        with pytest.raises(IntegrityError), connection.begin():
            connection.execute(insert(recipe_ingredients).values(recipe_id=99999, product_id=99999))
