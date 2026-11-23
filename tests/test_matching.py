import pytest

from app.matching import match_recipes


def recipe(recipe_id, name, ingredient_ids):
    return {
        "id": recipe_id,
        "name": name,
        "instructions": "Приготовить.",
        "ingredients": [{"id": item, "name": str(item)} for item in ingredient_ids],
    }


def test_full_match():
    result = match_recipes([recipe(1, "Омлет", [1, 2])], [1, 2])[0]
    assert result["percentage"] == 100.0
    assert [item["id"] for item in result["available_ingredients"]] == [1, 2]
    assert result["missing_ingredients"] == []


def test_partial_match():
    result = match_recipes([recipe(1, "Блины", [1, 2, 3])], [1])[0]
    assert result["percentage"] == 33.3
    assert [item["id"] for item in result["available_ingredients"]] == [1]
    assert [item["id"] for item in result["missing_ingredients"]] == [2, 3]


def test_zero_match_is_excluded():
    assert match_recipes([recipe(1, "Салат", [2, 3])], [1]) == []


def test_repeated_selected_products_do_not_increase_percentage():
    recipes = [recipe(1, "Омлет", [1, 2])]
    assert match_recipes(recipes, [1, 1, 1]) == match_recipes(recipes, [1])
    assert match_recipes(recipes, [1, 1])[0]["percentage"] == 50.0


def test_sort_by_percentage_then_name_then_id():
    recipes = [
        recipe(5, "Яичница", [1]),
        recipe(3, "Блины", [1, 2]),
        recipe(2, "Блины", [1, 2]),
        recipe(1, "Омлет", [1, 2]),
        recipe(4, "Салат", [2]),
    ]
    assert [item["id"] for item in match_recipes(recipes, [1])] == [5, 2, 3, 1]


def test_sort_uses_exact_ratio_before_rounding():
    recipes = [
        recipe(1, "А", range(1, 2001)),
        recipe(2, "Я", range(1, 2002)),
    ]
    results = match_recipes(recipes, range(2, 2002))
    assert [item["percentage"] for item in results] == [100.0, 100.0]
    assert [item["id"] for item in results] == [2, 1]


def test_empty_selection():
    with pytest.raises(ValueError, match="Выберите хотя бы один"):
        match_recipes([recipe(1, "Омлет", [1])], [])
