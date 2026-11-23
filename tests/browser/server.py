from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from app.main import create_app
from app.seed import seed_database

if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        app = create_app(Path(directory) / "recipes.db")
        seed_database(app.state.engine)
        uvicorn.run(app, host="127.0.0.1", port=18794)
