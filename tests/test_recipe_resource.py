"""Unit tests for src/resources/recipe.py — ensure_recipe + list_recipes."""

import json

import aiosqlite
import pytest

from src.resources.recipe import ensure_recipe
from src.resources.recipe import get_recipe
from src.resources.recipe import init_db
from src.resources.recipe import list_recipes


@pytest.fixture
async def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


@pytest.mark.anyio
async def test_ensure_recipe_creates_placeholder(db_path: str) -> None:
    await ensure_recipe("rid-1", db_path)
    recipe = await get_recipe("rid-1", db_path)
    assert recipe is not None
    assert recipe["id"] == "rid-1"


@pytest.mark.anyio
async def test_ensure_recipe_is_noop_on_second_call(db_path: str) -> None:
    await ensure_recipe("rid-2", db_path)
    await ensure_recipe("rid-2", db_path)  # must not raise or overwrite
    recipe = await get_recipe("rid-2", db_path)
    assert recipe is not None
    assert recipe["id"] == "rid-2"


@pytest.mark.anyio
async def test_ensure_recipe_placeholder_has_valid_fields(db_path: str) -> None:
    await ensure_recipe("rid-3", db_path)
    recipe = await get_recipe("rid-3", db_path)
    assert recipe is not None
    assert recipe["name"] == "New Recipe"
    assert recipe["fermentables"] == []
    assert recipe["hops"] == []
    assert recipe["yeast"]["attenuation_pct"] == 75.0
    assert recipe["batch_size_liters"] == 20.0


@pytest.mark.anyio
async def test_list_recipes_skips_rows_missing_required_keys(db_path: str) -> None:
    # Insert one valid and one stub (id-only) row directly
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO recipes (id, json) VALUES (?, ?)",
            ("stub-only", json.dumps({"id": "stub-only"})),
        )
        await db.commit()
    await ensure_recipe("valid-1", db_path)

    recipes = await list_recipes(db_path)
    ids = [r["id"] for r in recipes]
    assert "valid-1" in ids
    assert "stub-only" not in ids
