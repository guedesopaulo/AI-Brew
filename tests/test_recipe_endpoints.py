"""Smoke tests for recipe endpoints (resource layer mocked)."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.models.recipe import Recipe

RECIPE_STUB: Recipe = {
    "id": "abc-123",
    "name": "Test IPA",
    "style": "American IPA",
    "batch_size_liters": 20.0,
    "fermentables": [
        {"name": "Pale Malt (2-Row)", "amount_kg": 4.5, "color_ebc": 5, "ppg": 37}
    ],
    "hops": [
        {
            "name": "Cascade",
            "amount_g": 30,
            "alpha_pct": 5.5,
            "time_min": 60,
            "use": "boil",
        }
    ],
    "yeast": {
        "name": "SafAle US-05",
        "attenuation_pct": 78,
        "min_temp_c": 15,
        "max_temp_c": 24,
    },
}


@pytest.fixture
def client() -> TestClient:
    from src.main import app

    return TestClient(app, raise_server_exceptions=True)


def _auth() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# POST /recipe
# ---------------------------------------------------------------------------


def test_post_recipe_creates_and_returns_id(client: TestClient) -> None:
    with patch(
        "src.endpoints.recipe.create_recipe", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = "abc-123"
        response = client.post("/recipe", json=RECIPE_STUB, headers=_auth())

    assert response.status_code == 201
    assert response.json() == {"id": "abc-123"}


# ---------------------------------------------------------------------------
# GET /recipe/{id}
# ---------------------------------------------------------------------------


def test_get_recipe_returns_stats(client: TestClient) -> None:
    with patch("src.endpoints.recipe.get_recipe", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = RECIPE_STUB
        response = client.get("/recipe/abc-123", headers=_auth())

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "abc-123"
    assert "calculated" in data
    assert set(data["calculated"].keys()) == {"og", "fg", "abv", "ibu", "srm"}


def test_get_recipe_not_found(client: TestClient) -> None:
    with patch("src.endpoints.recipe.get_recipe", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get("/recipe/missing", headers=_auth())

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /recipe/{id}
# ---------------------------------------------------------------------------


def test_patch_recipe_updates_and_returns_stats(client: TestClient) -> None:
    updated: Recipe = {**RECIPE_STUB, "name": "Updated IPA"}
    with patch(
        "src.endpoints.recipe.update_recipe", new_callable=AsyncMock
    ) as mock_update:
        mock_update.return_value = updated
        response = client.patch(
            "/recipe/abc-123",
            json={"name": "Updated IPA"},
            headers=_auth(),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated IPA"
    assert "calculated" in data


def test_patch_recipe_not_found(client: TestClient) -> None:
    with patch(
        "src.endpoints.recipe.update_recipe", new_callable=AsyncMock
    ) as mock_update:
        mock_update.return_value = None
        response = client.patch("/recipe/missing", json={"name": "x"}, headers=_auth())

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /recipes
# ---------------------------------------------------------------------------


def test_get_recipes_returns_list(client: TestClient) -> None:
    with patch(
        "src.endpoints.recipe.list_recipes", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = [RECIPE_STUB]
        response = client.get("/recipes", headers=_auth())

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "abc-123"
    assert "calculated" in data[0]
    assert set(data[0]["calculated"].keys()) == {"og", "fg", "abv", "ibu", "srm"}


def test_get_recipes_empty(client: TestClient) -> None:
    with patch(
        "src.endpoints.recipe.list_recipes", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = []
        response = client.get("/recipes", headers=_auth())

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /recipe/{id}/profile
# ---------------------------------------------------------------------------


def test_get_recipe_profile_returns_sensory(client: TestClient) -> None:
    sensory = {
        "aroma": "citrus",
        "flavor": "hoppy",
        "mouthfeel": "medium",
        "appearance": "golden",
    }

    @asynccontextmanager
    async def _mock_agent_ctx(recipe_id: str) -> AsyncGenerator[MagicMock]:
        agent = MagicMock()
        # Simulate real case: JSON in ToolMessage, final AIMessage is empty.
        tool_msg = MagicMock()
        tool_msg.content = json.dumps(sensory)
        final_msg = MagicMock()
        final_msg.content = ""
        agent.ainvoke = AsyncMock(return_value={"messages": [tool_msg, final_msg]})
        yield agent

    with (
        patch("src.endpoints.recipe.get_recipe", new_callable=AsyncMock) as mock_get,
        patch("src.endpoints.recipe.recipe_agent_context", _mock_agent_ctx),
    ):
        mock_get.return_value = RECIPE_STUB
        response = client.get("/recipe/abc-123/profile", headers=_auth())

    assert response.status_code == 200
    data = response.json()
    assert data == sensory


def test_get_recipe_profile_not_found(client: TestClient) -> None:
    with patch("src.endpoints.recipe.get_recipe", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get("/recipe/missing/profile", headers=_auth())

    assert response.status_code == 404


def test_get_recipe_profile_no_profile_in_messages_returns_422(
    client: TestClient,
) -> None:
    @asynccontextmanager
    async def _mock_agent_ctx(recipe_id: str) -> AsyncGenerator[MagicMock]:
        agent = MagicMock()
        msg = MagicMock()
        msg.content = "Sure! Here's the sensory profile: it smells great."
        agent.ainvoke = AsyncMock(return_value={"messages": [msg]})
        yield agent

    with (
        patch("src.endpoints.recipe.get_recipe", new_callable=AsyncMock) as mock_get,
        patch("src.endpoints.recipe.recipe_agent_context", _mock_agent_ctx),
    ):
        mock_get.return_value = RECIPE_STUB
        response = client.get("/recipe/abc-123/profile", headers=_auth())

    assert response.status_code == 422
    assert "did not return" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /recipe/{id}/notes
# ---------------------------------------------------------------------------


def test_get_recipe_notes_returns_content_when_file_exists(
    client: TestClient, tmp_path: Path
) -> None:
    notes_dir = tmp_path / "brew_notes"
    notes_dir.mkdir()
    (notes_dir / "abc-123.md").write_text("# My Brew Notes")
    with patch("src.endpoints.recipe._REPO_ROOT", tmp_path):
        response = client.get("/recipe/abc-123/notes", headers=_auth())
    assert response.status_code == 200
    assert response.json() == {"content": "# My Brew Notes"}


def test_get_recipe_notes_returns_empty_when_no_file(
    client: TestClient, tmp_path: Path
) -> None:
    (tmp_path / "brew_notes").mkdir()
    with patch("src.endpoints.recipe._REPO_ROOT", tmp_path):
        response = client.get("/recipe/no-notes/notes", headers=_auth())
    assert response.status_code == 200
    assert response.json() == {"content": ""}


# ---------------------------------------------------------------------------
# GET /recipes/styles
# ---------------------------------------------------------------------------


def test_get_styles_returns_list(client: TestClient) -> None:
    response = client.get("/recipes/styles", headers=_auth())
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert {"name", "category", "og_min", "og_max", "ibu_min", "abv_min"}.issubset(
        first.keys()
    )


def test_get_styles_contains_known_style(client: TestClient) -> None:
    response = client.get("/recipes/styles", headers=_auth())
    names = [s["name"] for s in response.json()]
    assert "American IPA" in names


# ---------------------------------------------------------------------------
# GET /recipe/{id}/profile (existing tests follow)
# ---------------------------------------------------------------------------


def test_get_recipe_profile_passes_thread_id(client: TestClient) -> None:
    captured: dict[str, object] = {}

    @asynccontextmanager
    async def _mock_agent_ctx(recipe_id: str) -> AsyncGenerator[MagicMock]:
        agent = MagicMock()
        msg = MagicMock()
        msg.content = json.dumps(
            {"aroma": "a", "flavor": "b", "mouthfeel": "c", "appearance": "d"}
        )

        async def _ainvoke(inp: object, config: dict) -> dict:
            captured["thread_id"] = config["configurable"]["thread_id"]
            return {"messages": [msg]}

        agent.ainvoke = _ainvoke
        yield agent

    with (
        patch("src.endpoints.recipe.get_recipe", new_callable=AsyncMock) as mock_get,
        patch("src.endpoints.recipe.recipe_agent_context", _mock_agent_ctx),
    ):
        mock_get.return_value = RECIPE_STUB
        client.get("/recipe/abc-123/profile", headers=_auth())

    assert captured.get("thread_id") == "profile-abc-123"
