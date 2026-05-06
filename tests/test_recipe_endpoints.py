"""Smoke tests for recipe endpoints (resource layer mocked)."""

from unittest.mock import AsyncMock
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


def test_get_recipes_empty(client: TestClient) -> None:
    with patch(
        "src.endpoints.recipe.list_recipes", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = []
        response = client.get("/recipes", headers=_auth())

    assert response.status_code == 200
    assert response.json() == []
