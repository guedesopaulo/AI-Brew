"""Equipment profile TypedDicts."""

from typing import TypedDict


class EquipmentProfile(TypedDict):
    id: str
    name: str
    brewhouse_efficiency_pct: float  # e.g. 75.0 for a typical 3-vessel system
    batch_size_liters: float
    boil_volume_liters: float
    trub_loss_liters: float


class EquipmentProfilePatch(TypedDict, total=False):
    name: str
    brewhouse_efficiency_pct: float
    batch_size_liters: float
    boil_volume_liters: float
    trub_loss_liters: float


class EquipmentProfileCreate(TypedDict):
    name: str
    brewhouse_efficiency_pct: float
    batch_size_liters: float
    boil_volume_liters: float
    trub_loss_liters: float
