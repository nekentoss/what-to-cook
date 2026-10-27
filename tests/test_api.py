import pytest


def test_empty_database_and_static_pages(client):
    assert client.get("/api/products").json() == []
    assert client.get("/api/recipes").json() == []
    assert "Что приготовить?" in client.get("/").text
    assert client.get("/docs").status_code == 200
    assert "/api/matches" in client.get("/openapi.json").json()["paths"]
    assert client.get("/static/app.js").status_code == 200


def test_create_and_read_recipe(client, products, recipe_payload):
    recipe_payload["name"] = " Омлет "
    response = client.post("/api/recipes", json=recipe_payload)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Омлет"
    assert created["instructions"] == recipe_payload["instructions"]
    assert {item["id"] for item in created["ingredients"]} == set(recipe_payload["ingredient_ids"])
    assert client.get(f'/api/recipes/{created["id"]}').json() == created
    assert client.get("/api/recipes").json() == [created]


def test_edit_and_delete_recipe_keep_products(client, products, recipe_payload):
    created = client.post("/api/recipes", json=recipe_payload).json()
    path = f'/api/recipes/{created["id"]}'
    updated = {
        "name": "Омлет с сыром", "instructions": "Добавить сыр.",
        "ingredient_ids": [products[0]["id"], products[2]["id"]],
    }
    response = client.put(path, json=updated)
    assert response.status_code == 200
    assert response.json()["name"] == updated["name"]
    assert response.json()["instructions"] == updated["instructions"]
    assert {item["id"] for item in response.json()["ingredients"]} == set(updated["ingredient_ids"])
    assert client.get(path).json() == response.json()
    response = client.delete(path)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(path).status_code == 404
    assert client.get("/api/recipes").json() == []
    assert {item["id"] for item in client.get("/api/products").json()} == {item["id"] for item in products}


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_missing_recipe(client, recipe_payload, method):
    kwargs = {"json": recipe_payload} if method == "PUT" else {}
    response = client.request(method, "/api/recipes/99999", **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"] == "Рецепт не найден."


@pytest.mark.parametrize("changes", [
    {"name": ""}, {"name": " \t\n "}, {"name": None},
    {"instructions": ""}, {"instructions": "   "},
    {"ingredient_ids": []}, {"ingredient_ids": [1, 1]},
    {"ingredient_ids": [99999]}, {"ingredient_ids": [1, 99999]},
    {"ingredient_ids": [-1]}, {"ingredient_ids": [True]},
    {"ingredient_ids": [1.5]}, {"ingredient_ids": ["1"]},
])
def test_reject_invalid_recipe(client, recipe_payload, changes):
    response = client.post("/api/recipes", json={**recipe_payload, **changes})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert client.get("/api/recipes").json() == []


def test_required_fields(client):
    response = client.post("/api/recipes", json={})
    assert response.status_code == 422
    assert "обязательное поле" in response.json()["detail"]


def test_invalid_update_does_not_change_recipe(client, recipe_payload):
    created = client.post("/api/recipes", json=recipe_payload).json()
    path = f'/api/recipes/{created["id"]}'
    response = client.put(path, json={**recipe_payload, "name": "Другое имя", "ingredient_ids": [99999]})
    assert response.status_code == 422
    assert "99999" in response.json()["detail"]
    assert client.get(path).json() == created


def test_duplicate_product_is_case_insensitive_in_russian(client):
    first = client.post("/api/products", json={"name": " Молоко "})
    assert first.status_code == 201
    assert first.json()["name"] == "Молоко"
    response = client.post("/api/products", json={"name": "  мОЛОКО  "})
    assert response.status_code == 409
    assert "уже существует" in response.json()["detail"]
    assert client.get("/api/products").json() == [first.json()]
    assert client.post("/api/products", json={"name": "Сыр"}).status_code == 201


@pytest.mark.parametrize("name", ["", " \t\n ", None])
def test_invalid_product(client, name):
    assert client.post("/api/products", json={"name": name}).status_code == 422
    assert client.get("/api/products").json() == []


@pytest.mark.parametrize("selection", [[], [99999], [1, 99999], [True], ["1"]])
def test_invalid_selection(client, products, selection):
    response = client.post("/api/matches", json={"product_ids": selection})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_matching_api_and_duplicates(client, products, recipe_payload):
    created = client.post("/api/recipes", json=recipe_payload).json()
    selected = products[0]["id"]
    response = client.post("/api/matches", json={"product_ids": [selected, selected]})
    assert response.status_code == 200
    result = response.json()[0]
    assert result["id"] == created["id"]
    assert result["percentage"] == 50.0
    assert result["available_ingredients"] == [products[0]]
    assert result["missing_ingredients"] == [products[1]]
    full = client.post("/api/matches", json={"product_ids": recipe_payload["ingredient_ids"]}).json()
    assert full[0]["percentage"] == 100.0
    assert full[0]["missing_ingredients"] == []
    assert client.post("/api/matches", json={"product_ids": [products[2]["id"]]}).json() == []


def test_matching_api_sort_order(client, products):
    ids = [product["id"] for product in products]
    created = []
    for name, ingredients in [("Я", ids[:2]), ("А", ids[:2]), ("А", ids[:2]), ("Я", ids[:1])]:
        response = client.post("/api/recipes", json={
            "name": name, "instructions": "Приготовить.", "ingredient_ids": ingredients,
        })
        created.append(response.json()["id"])
    result = client.post("/api/matches", json={"product_ids": ids[:1]}).json()
    assert [recipe["id"] for recipe in result] == [created[3], created[1], created[2], created[0]]
