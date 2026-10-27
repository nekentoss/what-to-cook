from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProductId = Annotated[int, Field(strict=True, gt=0)]


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class RecipeWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    ingredient_ids: list[ProductId] = Field(min_length=1)

    @field_validator("ingredient_ids")
    @classmethod
    def unique_ingredients(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Один продукт не должен повторяться в составе рецепта.")
        return value


class RecipeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    instructions: str
    ingredients: list[ProductRead]


class MatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_ids: list[ProductId] = Field(min_length=1)


class MatchRead(RecipeRead):
    percentage: float
    available_ingredients: list[ProductRead]
    missing_ingredients: list[ProductRead]
