import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listEquipmentProfiles,
  createEquipmentProfile,
  patchEquipmentProfile,
  deleteEquipmentProfile,
} from "@/api/equipment";
import type { EquipmentProfilePatch } from "@/types/equipment";

export function useEquipmentProfiles() {
  return useQuery({
    queryKey: ["equipment"],
    queryFn: listEquipmentProfiles,
  });
}

export function useCreateEquipment(recipeId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createEquipmentProfile,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["equipment"] });
      if (recipeId) {
        void queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
      }
    },
  });
}

// Note: usePatchEquipment cannot invalidate ['recipe', id] because it has no
// recipeId param. If an equipment profile's efficiency is edited from a future
// management page, the open recipe detail view will show stale stats until
// the user navigates away and back. Acceptable until an equipment editor UI exists.
export function usePatchEquipment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: EquipmentProfilePatch }) =>
      patchEquipmentProfile(id, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["equipment"] });
      void queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });
}

export function useDeleteEquipment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteEquipmentProfile,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["equipment"] });
    },
  });
}
