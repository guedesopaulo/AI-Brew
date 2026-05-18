export interface EquipmentProfile {
  id: string;
  name: string;
  brewhouse_efficiency_pct: number;
  batch_size_liters: number;
  boil_volume_liters: number;
  trub_loss_liters: number;
}

export type EquipmentProfilePatch = Partial<Omit<EquipmentProfile, "id">>;

export interface EquipmentProfileCreate {
  name: string;
  brewhouse_efficiency_pct: number;
  batch_size_liters: number;
  boil_volume_liters: number;
  trub_loss_liters: number;
}
