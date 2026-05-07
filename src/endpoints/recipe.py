"""Recipe CRUD endpoints."""

from fastapi import APIRouter
from fastapi import HTTPException

from src.config import settings
from src.models.recipe import Recipe
from src.models.recipe import RecipePatch
from src.models.recipe import RecipeWithStats
from src.resources.recipe import create_recipe
from src.resources.recipe import get_recipe
from src.resources.recipe import list_recipes
from src.resources.recipe import update_recipe
from src.service.recipe import calculate_stats

router = APIRouter(prefix="/recipe", tags=["recipe"])


@router.post("", status_code=201)
async def post_recipe(recipe: Recipe) -> dict[str, str]:
    recipe_id = await create_recipe(recipe, settings.DB_PATH)
    return {"id": recipe_id}


@router.get("/{recipe_id}")
async def get_recipe_by_id(recipe_id: str) -> RecipeWithStats:
    recipe = await get_recipe(recipe_id, settings.DB_PATH)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {**recipe, "calculated": calculate_stats(recipe)}


@router.patch("/{recipe_id}")
async def patch_recipe(recipe_id: str, patch: RecipePatch) -> RecipeWithStats:
    updated = await update_recipe(recipe_id, patch, settings.DB_PATH)
    if updated is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {**updated, "calculated": calculate_stats(updated)}


@router.get("s")
async def get_recipes() -> list[Recipe]:
    return await list_recipes(settings.DB_PATH)
