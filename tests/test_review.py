import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.main import create_app
from app.models import Recipe
from app.seed import seed_database


def test_upgrade_keeps_existing_recipe_and_does_not_reuse_its_id(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                                   normalized_name TEXT NOT NULL UNIQUE);
            CREATE TABLE recipes (id INTEGER PRIMARY KEY, name TEXT NOT NULL, instructions TEXT NOT NULL);
            CREATE TABLE recipe_ingredients (
                recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id), PRIMARY KEY(recipe_id, product_id));
            INSERT INTO products VALUES (3, 'Сыр', 'сыр');
            INSERT INTO recipes VALUES (7, 'Первый', 'Нарезать');
            INSERT INTO recipe_ingredients VALUES (7, 3);
        """)
    for _ in range(2):
        with TestClient(create_app(path)) as client:
            assert client.get("/api/recipes/7").json()["ingredients"] == [{"id": 3, "name": "Сыр"}]
    with TestClient(create_app(path)) as client:
        assert client.delete("/api/recipes/7").status_code == 204
        created = client.post(
            "/api/recipes",
            json={"name": "Второй", "instructions": "Нарезать", "ingredient_ids": [3]},
        )
        assert created.status_code == 201
        assert created.json()["id"] > 7
        assert client.delete("/api/recipes/7").status_code == 404
        assert client.get("/api/recipes").json() == [created.json()]


def test_database_names_with_question_marks_are_independent(tmp_path):
    for name in ("ужин?пт.db", "ужин?сб.db"):
        with TestClient(create_app(tmp_path / name)) as client:
            assert client.get("/api/products").json() == []
            assert client.post("/api/products", json={"name": "Сыр"}).status_code == 201
        assert (tmp_path / name).is_file()


def test_matches_load_only_candidates(client):
    seed_database(client.app.state.engine)
    milk = next(p["id"] for p in client.get("/api/products").json() if p["name"] == "Молоко")
    loaded = []

    def remember(recipe, context):
        loaded.append(recipe.id)

    event.listen(Recipe, "load", remember)
    try:
        response = client.post("/api/matches", json={"product_ids": [milk]})
    finally:
        event.remove(Recipe, "load", remember)
    assert response.status_code == 200
    rows = response.json()
    assert [r["name"] for r in rows] == ["Омлет", "Блины"]
    assert sorted(loaded) == sorted(r["id"] for r in rows)
    assert [r["percentage"] for r in rows] == [25.0, 16.7]


def test_error_matches_openapi_schema(client):
    schema = client.get("/openapi.json").json()
    error = schema["paths"]["/api/matches"]["post"]["responses"]["422"]
    name = error["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
    assert schema["components"]["schemas"][name]["properties"]["detail"]["type"] == "string"
    response = client.post("/api/matches", json={"product_ids": []})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
