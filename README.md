# Что приготовить?

Приложение подбирает рецепты по продуктам, которые есть дома. Для каждого рецепта показывает процент совпадения и недостающие ингредиенты. Через интерфейс можно добавлять продукты, создавать, изменять и удалять рецепты.

Один сервер FastAPI обслуживает API и страницу на обычном JavaScript. Данные хранятся в SQLite. [ТЗ](SPEC.md) · [Использование AI](AI_USAGE.md)

## Запуск через Docker

```bash
docker compose up --build -d
docker compose exec web python -m app.seed
```

[Приложение](http://127.0.0.1:8000) · [Swagger](http://127.0.0.1:8000/docs). В демобазе 15 продуктов и 6 рецептов. Повторное заполнение сохраняет пользовательские данные. Команда `docker compose down` останавливает приложение, база остаётся в томе. Исходники подключены к контейнеру, сервер перезагружается при изменениях.

## Локальный запуск и проверки

Из корня проекта, с Python 3.9 и Node.js 22 или новее:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci
pre-commit install
python -m app.seed
python -m uvicorn app.main:app --reload
```

По умолчанию файл базы — `data/recipes.db`. Переменная `DATABASE_PATH` задаёт другой путь.

```bash
pre-commit run --all-files
python -m pytest tests/test_matching.py --cov=app.matching --cov-fail-under=60
python -m pytest --cov=app --cov-report=term-missing
```

Ruff проверяет и форматирует Python, Biome — JavaScript. GitHub Actions запускает проверки при push и для Pull Request. XML-отчёт о покрытии сохраняется в артефакте `coverage`. [Успешная проверка](https://github.com/nekentoss/what-to-cook/actions/runs/45100903792) · [Падение линтера в PR № 4](https://github.com/nekentoss/what-to-cook/actions/runs/45006356940)

## Материалы проекта

- [Ревью исходного MVP](REVIEW.md) и [бэклог](TODO.md)
- [Метрики до рефакторинга](ANALYSIS.md) и [результаты после](REFACTORING.md)
- [Презентация к защите, 4 слайда](docs/defense.pdf)
- [Лог успешной проверки](docs/ci.txt)

Для проверки интерфейса нужен Google Chrome. Из активированного окружения запустите `npm run test:ui`. Тесты используют отдельную временную базу.

Ветка `mvp` хранит исходный код от AI. Изменения попадают в `main` через Pull Request с обязательной проверкой `Quality Gate`.
