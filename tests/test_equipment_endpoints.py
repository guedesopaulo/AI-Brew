"""Smoke tests for equipment profile endpoints (resource layer mocked)."""

from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.models.equipment import EquipmentProfile

PROFILE_STUB: EquipmentProfile = {
    "id": "equip-1",
    "name": "My BIAB",
    "brewhouse_efficiency_pct": 68.0,
    "batch_size_liters": 20.0,
    "boil_volume_liters": 27.0,
    "trub_loss_liters": 1.5,
}


@pytest.fixture
def client() -> TestClient:
    from src.main import app

    return TestClient(app, raise_server_exceptions=True)


def _auth() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_post_equipment_creates_profile(client: TestClient) -> None:
    with patch(
        "src.endpoints.equipment.create_equipment_profile",
        new=AsyncMock(return_value="equip-1"),
    ):
        resp = client.post("/equipment", json=PROFILE_STUB, headers=_auth())
    assert resp.status_code == 201
    assert resp.json()["id"] == "equip-1"


def test_get_equipment_by_id_returns_profile(client: TestClient) -> None:
    with patch(
        "src.endpoints.equipment.get_equipment_profile",
        new=AsyncMock(return_value=PROFILE_STUB),
    ):
        resp = client.get("/equipment/equip-1", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["name"] == "My BIAB"
    assert resp.json()["brewhouse_efficiency_pct"] == 68.0


def test_get_equipment_by_id_not_found(client: TestClient) -> None:
    with patch(
        "src.endpoints.equipment.get_equipment_profile",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/equipment/missing", headers=_auth())
    assert resp.status_code == 404


def test_patch_equipment_updates_field(client: TestClient) -> None:
    updated = {**PROFILE_STUB, "brewhouse_efficiency_pct": 72.0}
    with patch(
        "src.endpoints.equipment.update_equipment_profile",
        new=AsyncMock(return_value=updated),
    ):
        resp = client.patch(
            "/equipment/equip-1",
            json={"brewhouse_efficiency_pct": 72.0},
            headers=_auth(),
        )
    assert resp.status_code == 200
    assert resp.json()["brewhouse_efficiency_pct"] == 72.0


def test_delete_equipment_returns_204(client: TestClient) -> None:
    with patch(
        "src.endpoints.equipment.delete_equipment_profile",
        new=AsyncMock(return_value=True),
    ):
        resp = client.delete("/equipment/equip-1", headers=_auth())
    assert resp.status_code == 204


def test_list_equipment_returns_profiles(client: TestClient) -> None:
    with patch(
        "src.endpoints.equipment.list_equipment_profiles",
        new=AsyncMock(return_value=[PROFILE_STUB]),
    ):
        resp = client.get("/equipments", headers=_auth())
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "My BIAB"
