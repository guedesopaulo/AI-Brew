import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateEquipment } from "@/hooks/useEquipment";
import { patchRecipe } from "@/api/recipes";
import { useQueryClient } from "@tanstack/react-query";

interface CreateEquipmentDialogProps {
  recipeId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const DEFAULT_FORM = {
  name: "",
  brewhouse_efficiency_pct: 75,
  batch_size_liters: 20,
  boil_volume_liters: 25,
  trub_loss_liters: 1,
};

export function CreateEquipmentDialog({
  recipeId,
  open,
  onOpenChange,
}: CreateEquipmentDialogProps) {
  const queryClient = useQueryClient();
  const createEquipment = useCreateEquipment(recipeId);
  const [form, setForm] = useState(DEFAULT_FORM);

  async function handleCreate() {
    const result = await createEquipment.mutateAsync(form);
    await patchRecipe(recipeId, { equipment_id: result.id });
    void queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
    void queryClient.invalidateQueries({ queryKey: ["recipes"] });
    onOpenChange(false);
    setForm(DEFAULT_FORM);
  }

  function updateForm(field: keyof typeof DEFAULT_FORM, value: string) {
    const numFields = [
      "brewhouse_efficiency_pct",
      "batch_size_liters",
      "boil_volume_liters",
      "trub_loss_liters",
    ] as const;
    setForm((prev) => ({
      ...prev,
      [field]: numFields.includes(field as (typeof numFields)[number])
        ? parseFloat(value) || 0
        : value,
    }));
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => onOpenChange(o)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New equipment profile</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-3 pt-2">
          <div className="col-span-2 space-y-1">
            <Label>Name</Label>
            <Input
              value={form.name}
              placeholder="e.g. My BIAB system"
              onChange={(e) => updateForm("name", e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Efficiency (%)</Label>
            <Input
              type="number"
              value={form.brewhouse_efficiency_pct}
              onChange={(e) =>
                updateForm("brewhouse_efficiency_pct", e.target.value)
              }
            />
          </div>
          <div className="space-y-1">
            <Label>Batch size (L)</Label>
            <Input
              type="number"
              value={form.batch_size_liters}
              onChange={(e) => updateForm("batch_size_liters", e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Boil volume (L)</Label>
            <Input
              type="number"
              value={form.boil_volume_liters}
              onChange={(e) => updateForm("boil_volume_liters", e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Trub loss (L)</Label>
            <Input
              type="number"
              value={form.trub_loss_liters}
              onChange={(e) => updateForm("trub_loss_liters", e.target.value)}
            />
          </div>
          <div className="col-span-2 flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => void handleCreate()}
              disabled={!form.name || createEquipment.isPending}
            >
              {createEquipment.isPending ? "Creating…" : "Create & select"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
