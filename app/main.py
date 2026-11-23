from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.database import get_session, init_database, make_engine
from app.matching import match_recipes
from app.models import Product, Recipe
from app.schemas import (
    ErrorResponse,
    MatchRead,
    MatchRequest,
    ProductCreate,
    ProductRead,
    RecipeRead,
    RecipeWrite,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def find_recipe(session, recipe_id):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(404, "Рецепт не найден.")
    return recipe


def find_products(session, product_ids):
    products = session.scalars(
        select(Product).where(Product.id.in_(product_ids)).order_by(Product.name)
    ).all()
    missing = set(product_ids) - {product.id for product in products}
    if missing:
        ids = ", ".join(str(product_id) for product_id in sorted(missing))
        raise HTTPException(422, "Не найдены продукты с ID: " + ids + ".")
    return products


def create_app(database_path=None):
    engine = make_engine(database_path)

    @asynccontextmanager
    async def lifespan(application):
        init_database(engine)
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Что приготовить?", version="0.1.0", lifespan=lifespan)
    application.state.engine = engine
    application.state.session_factory = sessionmaker(bind=engine)
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        fields = {
            "name": "Название",
            "instructions": "Инструкция",
            "ingredient_ids": "Ингредиенты",
            "product_ids": "Имеющиеся продукты",
        }
        messages = {
            "missing": "обязательное поле.",
            "string_too_short": "введите непустой текст.",
            "string_type": "ожидается текст.",
            "too_short": "выберите хотя бы один продукт.",
            "int_type": "ID должен быть целым числом.",
            "greater_than": "ID должен быть положительным числом.",
            "list_type": "ожидается список ID продуктов.",
            "extra_forbidden": "неизвестное поле.",
            "json_invalid": "некорректный JSON.",
        }
        details = []
        for item in error.errors():
            field = next((fields[part] for part in item["loc"] if part in fields), "Данные")
            message = messages.get(item["type"], "некорректное значение.")
            if item["type"] == "value_error":
                message = item["msg"].removeprefix("Value error, ")
            details.append(field + ": " + message)
        return JSONResponse(status_code=422, content={"detail": " ".join(details)})

    validation_responses = {422: {"model": ErrorResponse}}

    @application.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/api/products", response_model=list[ProductRead], tags=["Продукты"])
    def list_products(session: Session = Depends(get_session)):
        return session.scalars(select(Product).order_by(Product.name, Product.id)).all()

    @application.post(
        "/api/products",
        responses=validation_responses,
        response_model=ProductRead,
        status_code=201,
        tags=["Продукты"],
    )
    def add_product(data: ProductCreate, session: Session = Depends(get_session)):
        product = Product(name=data.name, normalized_name=data.name.casefold())
        session.add(product)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "Продукт с таким названием уже существует.")
        session.refresh(product)
        return product

    @application.get("/api/recipes", response_model=list[RecipeRead], tags=["Рецепты"])
    def list_recipes(session: Session = Depends(get_session)):
        return session.scalars(
            select(Recipe)
            .options(selectinload(Recipe.ingredients))
            .order_by(Recipe.name, Recipe.id)
        ).all()

    @application.get(
        "/api/recipes/{recipe_id}",
        responses=validation_responses,
        response_model=RecipeRead,
        tags=["Рецепты"],
    )
    def get_recipe(recipe_id: int, session: Session = Depends(get_session)):
        return find_recipe(session, recipe_id)

    @application.post(
        "/api/recipes",
        responses=validation_responses,
        response_model=RecipeRead,
        status_code=201,
        tags=["Рецепты"],
    )
    def add_recipe(data: RecipeWrite, session: Session = Depends(get_session)):
        recipe = Recipe(
            name=data.name,
            instructions=data.instructions,
            ingredients=find_products(session, data.ingredient_ids),
        )
        session.add(recipe)
        session.commit()
        session.refresh(recipe)
        return recipe

    @application.put(
        "/api/recipes/{recipe_id}",
        responses=validation_responses,
        response_model=RecipeRead,
        tags=["Рецепты"],
    )
    def edit_recipe(recipe_id: int, data: RecipeWrite, session: Session = Depends(get_session)):
        recipe = find_recipe(session, recipe_id)
        products = find_products(session, data.ingredient_ids)
        recipe.name = data.name
        recipe.instructions = data.instructions
        recipe.ingredients = products
        session.commit()
        session.refresh(recipe)
        return recipe

    @application.delete(
        "/api/recipes/{recipe_id}",
        responses=validation_responses,
        status_code=204,
        tags=["Рецепты"],
    )
    def delete_recipe(recipe_id: int, session: Session = Depends(get_session)):
        session.delete(find_recipe(session, recipe_id))
        session.commit()
        return Response(status_code=204)

    @application.post(
        "/api/matches",
        responses=validation_responses,
        response_model=list[MatchRead],
        tags=["Подбор"],
    )
    def get_matches(data: MatchRequest, session: Session = Depends(get_session)):
        find_products(session, data.product_ids)
        recipes = session.scalars(
            select(Recipe)
            .where(Recipe.ingredients.any(Product.id.in_(set(data.product_ids))))
            .options(selectinload(Recipe.ingredients))
        ).all()
        return match_recipes(
            [RecipeRead.model_validate(recipe).model_dump() for recipe in recipes], data.product_ids
        )

    return application


app = create_app()
