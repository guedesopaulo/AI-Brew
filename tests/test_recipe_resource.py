"""Unit tests for src/resources/recipe.py — ensure_recipe."""

import pytest

from src.resources.recipe import ensure_recipe
from src.resources.recipe import get_recipe
from src.resources.recipe import init_db


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
