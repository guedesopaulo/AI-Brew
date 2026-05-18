import { apiFetch } from "./client";
import type { EquipmentProfile, EquipmentProfilePatch } from "@/types/equipment";

export async function listEquipmentProfiles(): Promise<EquipmentProfile[]> {
  return apiFetch<EquipmentProfile[]>("/equipments");
}

export async function getEquipmentProfile(id: string): Promise<EquipmentProfile> {
  return apiFetch<EquipmentProfile>(`/equipment/${id}`);
}

export async function createEquipmentProfile(
  profile: Omit<EquipmentProfile, "id">,
): Promise<{ id: string }> {
  return apiFetch<{ id: string }>("/equipment", {
    method: "POST",
    body: JSON.stringify(profile),
  });
}

export async function patchEquipmentProfile(
  id: string,
  patch: EquipmentProfilePatch,
): Promise<EquipmentProfile> {
  return apiFetch<EquipmentProfile>(`/equipment/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function deleteEquipmentProfile(id: string): Promise<void> {
  await apiFetch<void>(`/equipment/${id}`, { method: "DELETE" });
}
