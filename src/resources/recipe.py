"""aiosqlite CRUD for recipes."""

import json
import uuid

import aiosqlite

from src.models.recipe import Recipe
from src.models.recipe import RecipePatch


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await db.commit()


async def ensure_recipe(recipe_id: str, db_path: str) -> None:
    """Create a minimal valid recipe row if one doesn't already exist."""
    placeholder: Recipe = {
        "id": recipe_id,
        "name": "New Recipe",
        "style": "",
        "batch_size_liters": 20.0,
        "fermentables": [],
        "hops": [],
        "yeast": {
            "name": "",
            "attenuation_pct": 75.0,
            "min_temp_c": 18.0,
            "max_temp_c": 24.0,
        },
    }
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO recipes (id, json) VALUES (?, ?)",
            (recipe_id, json.dumps(placeholder)),
        )
        await db.commit()


async def create_recipe(recipe: Recipe, db_path: str) -> str:
    recipe_id = recipe.get("id") or str(uuid.uuid4())
    data: Recipe = {**recipe, "id": recipe_id}
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO recipes (id, json) VALUES (?, ?)",
            (recipe_id, json.dumps(data)),
        )
        await db.commit()
    return recipe_id


async def get_recipe(recipe_id: str, db_path: str) -> Recipe | None:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT json FROM recipes WHERE id = ?", (recipe_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return json.loads(row[0])


async def update_recipe(
    recipe_id: str, patch: RecipePatch, db_path: str
) -> Recipe | None:
    existing = await get_recipe(recipe_id, db_path)
    if existing is None:
        return None
    updated: Recipe = {**existing, **patch}
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE recipes SET json = ? WHERE id = ?",
            (json.dumps(updated), recipe_id),
        )
        await db.commit()
    return updated


_REQUIRED_RECIPE_KEYS = {
    "id",
    "name",
    "style",
    "batch_size_liters",
    "fermentables",
    "hops",
    "yeast",
}


async def list_recipes(db_path: str) -> list[Recipe]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT json FROM recipes ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
    results = []
    for row in rows:
        data = json.loads(row[0])
        if _REQUIRED_RECIPE_KEYS.issubset(data.keys()):
            results.append(data)
    return results
