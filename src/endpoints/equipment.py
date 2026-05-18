"""Equipment profile CRUD endpoints."""

import uuid

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Response

from src.config import settings
from src.models.equipment import EquipmentProfile
from src.models.equipment import EquipmentProfileCreate
from src.models.equipment import EquipmentProfilePatch
from src.resources.equipment import create_equipment_profile
from src.resources.equipment import delete_equipment_profile
from src.resources.equipment import get_equipment_profile
from src.resources.equipment import list_equipment_profiles
from src.resources.equipment import update_equipment_profile

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("", status_code=201)
async def post_equipment(profile: EquipmentProfileCreate) -> dict[str, str]:
    full: EquipmentProfile = {**profile, "id": str(uuid.uuid4())}
    profile_id = await create_equipment_profile(full, settings.DB_PATH)
    return {"id": profile_id}


@router.get("/{profile_id}")
async def get_equipment_by_id(profile_id: str) -> EquipmentProfile:
    profile = await get_equipment_profile(profile_id, settings.DB_PATH)
    if profile is None:
        raise HTTPException(status_code=404, detail="Equipment profile not found")
    return profile


@router.patch("/{profile_id}")
async def patch_equipment(
    profile_id: str, patch: EquipmentProfilePatch
) -> EquipmentProfile:
    updated = await update_equipment_profile(profile_id, patch, settings.DB_PATH)
    if updated is None:
        raise HTTPException(status_code=404, detail="Equipment profile not found")
    return updated


@router.delete("/{profile_id}", status_code=204)
async def delete_equipment_by_id(profile_id: str) -> Response:
    deleted = await delete_equipment_profile(profile_id, settings.DB_PATH)
    if not deleted:
        raise HTTPException(status_code=404, detail="Equipment profile not found")
    return Response(status_code=204)


@router.get("s")
async def list_equipment() -> list[EquipmentProfile]:
    return await list_equipment_profiles(settings.DB_PATH)
