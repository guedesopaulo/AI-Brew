import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useEquipmentProfiles } from "@/hooks/useEquipment";
import { patchRecipe } from "@/api/recipes";
import { useQueryClient } from "@tanstack/react-query";
import { CreateEquipmentDialog } from "@/components/CreateEquipmentDialog";

interface EquipmentSelectorProps {
  recipeId: string;
  currentEquipmentId?: string;
  disabled?: boolean;
}

export function EquipmentSelector({
  recipeId,
  currentEquipmentId,
  disabled,
}: EquipmentSelectorProps) {
  const queryClient = useQueryClient();
  const { data: profiles = [] } = useEquipmentProfiles();
  const [open, setOpen] = useState(false);

  async function handleSelect(value: string) {
    const equipmentId = value === "none" ? undefined : value;
    const profile = profiles.find((p) => p.id === value);
    await patchRecipe(recipeId, {
      equipment_id: equipmentId,
      ...(profile && { batch_size_liters: profile.batch_size_liters }),
    });
    void queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
    void queryClient.invalidateQueries({ queryKey: ["recipes"] });
  }

  const selectedProfile = profiles.find((p) => p.id === currentEquipmentId);

  return (
    <div className="space-y-1">
      <Label>Equipment profile</Label>
      <div className="flex gap-2">
        <Select
          value={currentEquipmentId ?? "none"}
          // Base UI types onValueChange as (value: string | null) for single-select
          onValueChange={(v) => v && void handleSelect(v)}
          disabled={disabled}
        >
          <SelectTrigger className="flex-1">
            <SelectValue placeholder="No profile (75% efficiency)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">No profile (75% default)</SelectItem>
            {profiles.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.name} — {p.brewhouse_efficiency_pct}%
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => setOpen(true)}
        >
          + New
        </Button>

        <CreateEquipmentDialog
          recipeId={recipeId}
          open={open}
          onOpenChange={setOpen}
        />
      </div>

      {selectedProfile && (
        <p className="text-xs text-muted-foreground">
          {selectedProfile.brewhouse_efficiency_pct}% efficiency ·{" "}
          {selectedProfile.batch_size_liters} L batch ·{" "}
          {selectedProfile.boil_volume_liters} L boil
        </p>
      )}
    </div>
  );
}
