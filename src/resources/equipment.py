"""aiosqlite CRUD for equipment profiles."""

import json

import aiosqlite

from src.models.equipment import EquipmentProfile
from src.models.equipment import EquipmentProfilePatch


async def init_equipment_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_profiles (
                id TEXT PRIMARY KEY,
                json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await db.commit()


async def create_equipment_profile(profile: EquipmentProfile, db_path: str) -> str:
    profile_id = profile["id"]
    data: EquipmentProfile = {**profile}
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO equipment_profiles (id, json) VALUES (?, ?)",
            (profile_id, json.dumps(data)),
        )
        await db.commit()
    return profile_id


async def get_equipment_profile(
    profile_id: str, db_path: str
) -> EquipmentProfile | None:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT json FROM equipment_profiles WHERE id = ?", (profile_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return json.loads(row[0])


async def update_equipment_profile(
    profile_id: str, patch: EquipmentProfilePatch, db_path: str
) -> EquipmentProfile | None:
    existing = await get_equipment_profile(profile_id, db_path)
    if existing is None:
        return None
    updated: EquipmentProfile = {**existing, **patch}
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE equipment_profiles SET json = ? WHERE id = ?",
            (json.dumps(updated), profile_id),
        )
        await db.commit()
    return updated


async def delete_equipment_profile(profile_id: str, db_path: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "DELETE FROM equipment_profiles WHERE id = ?", (profile_id,)
        )
        await db.commit()
    return cursor.rowcount > 0


async def list_equipment_profiles(db_path: str) -> list[EquipmentProfile]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT json FROM equipment_profiles ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
    return [json.loads(row[0]) for row in rows]


async def get_equipment_profiles_by_ids(
    ids: list[str], db_path: str
) -> dict[str, EquipmentProfile]:
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"SELECT json FROM equipment_profiles WHERE id IN ({placeholders})",
            ids,
        ) as cursor:
            rows = await cursor.fetchall()
    result: dict[str, EquipmentProfile] = {}
    for row in rows:
        profile: EquipmentProfile = json.loads(row[0])
        result[profile["id"]] = profile
    return result
