from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

recipe_ingredients = Table(
    "recipe_ingredients",
    Base.metadata,
    Column("recipe_id", ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", ForeignKey("products.id"), primary_key=True),
)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    # SQLite NOCASE не сравнивает кириллицу без учёта регистра.
    normalized_name = Column(String, nullable=False, unique=True)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    instructions = Column(Text, nullable=False)
    ingredients = relationship(Product, secondary=recipe_ingredients, order_by=Product.name)
