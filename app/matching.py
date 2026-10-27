from fractions import Fraction


def match_recipes(recipes, selected_ids):
    """Принимает обычные словари и ID, не обращается к HTTP или базе."""
    selected = set(selected_ids)
    if not selected:
        raise ValueError("Выберите хотя бы один имеющийся продукт.")

    results = []
    for recipe in recipes:
        ingredients = recipe["ingredients"]
        available = [item for item in ingredients if item["id"] in selected]
        if not available:
            continue
        missing = [item for item in ingredients if item["id"] not in selected]
        ratio = Fraction(len(available), len(ingredients))
        result = {
            **recipe,
            "percentage": round(float(ratio * 100), 1),
            "available_ingredients": available,
            "missing_ingredients": missing,
        }
        # Точная доля нужна для сортировки до округления процента.
        results.append((ratio, result))

    results.sort(key=lambda item: (-item[0], item[1]["name"], item[1]["id"]))
    return [result for _, result in results]
