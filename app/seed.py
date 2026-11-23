from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import init_database, make_engine
from app.models import Product, Recipe

PRODUCTS = [
    "Яйцо",
    "Молоко",
    "Мука",
    "Соль",
    "Сахар",
    "Масло растительное",
    "Помидор",
    "Огурец",
    "Лук",
    "Картофель",
    "Морковь",
    "Рис",
    "Курица",
    "Сыр",
    "Макароны",
]

RECIPES = [
    (
        "Омлет",
        "Взбейте яйца с молоком и солью. Разогрейте масло на сковороде. "
        "Влейте смесь и готовьте под крышкой до полной готовности яиц.",
        ["Яйцо", "Молоко", "Соль", "Масло растительное"],
    ),
    (
        "Овощной салат",
        "Нарежьте помидоры, огурцы и лук. Добавьте соль и масло, перемешайте.",
        ["Помидор", "Огурец", "Лук", "Соль", "Масло растительное"],
    ),
    (
        "Блины",
        "Смешайте яйца, молоко, муку, сахар и соль до однородности. "
        "Выпекайте тонкие блины с двух сторон на сковороде с маслом.",
        ["Яйцо", "Молоко", "Мука", "Сахар", "Соль", "Масло растительное"],
    ),
    (
        "Рис с курицей",
        "Нарежьте курицу, лук и морковь. Обжарьте на масле, добавьте рис, "
        "соль и воду. Тушите до готовности риса и полной готовности курицы.",
        ["Рис", "Курица", "Лук", "Морковь", "Соль", "Масло растительное"],
    ),
    (
        "Картофель с сыром",
        "Нарежьте картофель, посолите и смажьте маслом. "
        "Запекайте до мягкости, посыпьте сыром и верните в духовку до его расплавления.",
        ["Картофель", "Сыр", "Соль", "Масло растительное"],
    ),
    (
        "Макароны с сыром",
        "Отварите макароны в подсоленной воде. Слейте воду, добавьте тёртый сыр и перемешайте.",
        ["Макароны", "Сыр", "Соль"],
    ),
]


def seed_database(engine):
    init_database(engine)
    with Session(engine) as session:
        products = {item.normalized_name: item for item in session.scalars(select(Product))}
        added_products = 0
        for name in PRODUCTS:
            key = name.casefold()
            if key not in products:
                product = Product(name=name, normalized_name=key)
                session.add(product)
                products[key] = product
                added_products += 1

        existing_recipes = {
            name.strip().casefold() for name in session.scalars(select(Recipe.name))
        }
        added_recipes = 0
        for name, instructions, ingredient_names in RECIPES:
            if name.casefold() not in existing_recipes:
                session.add(
                    Recipe(
                        name=name,
                        instructions=instructions,
                        ingredients=[products[item.casefold()] for item in ingredient_names],
                    )
                )
                existing_recipes.add(name.casefold())
                added_recipes += 1
        session.commit()
    return added_products, added_recipes


if __name__ == "__main__":
    engine = make_engine()
    try:
        products, recipes = seed_database(engine)
        print(f"Добавлено продуктов: {products}; рецептов: {recipes}.")
    finally:
        engine.dispose()
