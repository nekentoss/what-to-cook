import os
from pathlib import Path

from fastapi import Request
from sqlalchemy import URL, create_engine, event

from app.models import Base, Recipe

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "recipes.db"


def make_engine(database_path=None):
    path = Path(database_path or os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))
    engine = create_engine(
        URL.create("sqlite", database=str(path.resolve())),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_database(engine):
    Path(engine.url.database).parent.mkdir(parents=True, exist_ok=True)
    with engine.begin() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        Base.metadata.create_all(connection)
        schema = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='recipes'"
        ).scalar_one()
        if "AUTOINCREMENT" not in schema.upper():
            upgrade_recipe_ids(connection)


def upgrade_recipe_ids(connection):
    """Обновляет таблицу MVP в одной транзакции, сохраняя состав рецептов."""
    run = connection.exec_driver_sql
    run("CREATE TEMP TABLE old_recipes AS SELECT id, name, instructions FROM recipes")
    run("CREATE TEMP TABLE old_links AS SELECT recipe_id, product_id FROM recipe_ingredients")
    run("DROP TABLE recipes")
    Recipe.__table__.create(connection)
    run(
        "INSERT INTO recipes (id, name, instructions) SELECT id, name, instructions FROM old_recipes"
    )
    run(
        "INSERT INTO recipe_ingredients (recipe_id, product_id) SELECT recipe_id, product_id FROM old_links"
    )
    run("DROP TABLE temp.old_links")
    run("DROP TABLE temp.old_recipes")


def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session
