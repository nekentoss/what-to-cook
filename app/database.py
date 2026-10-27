import os
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine, event

from app.models import Base


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "recipes.db"


def make_engine(database_path=None):
    path = Path(database_path or os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))
    engine = create_engine(
        "sqlite:///" + str(path.resolve()),
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
    Base.metadata.create_all(engine)


def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session
