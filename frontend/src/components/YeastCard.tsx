import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Yeast } from "@/types/recipe";

interface YeastCardProps {
  yeast: Yeast;
  onChange: (yeast: Yeast) => void;
  disabled?: boolean;
}

export function YeastCard({ yeast, onChange, disabled }: YeastCardProps) {
  const [local, setLocal] = useState<Yeast>(yeast);

  useEffect(() => {
    setLocal(yeast);
  }, [yeast]);

  function updateLocal(field: keyof Yeast, value: string) {
    const numFields: (keyof Yeast)[] = ["attenuation_pct", "min_temp_c", "max_temp_c"];
    setLocal((prev) => ({
      ...prev,
      [field]: numFields.includes(field) ? parseFloat(value) || 0 : value,
    }));
  }

  function commit() {
    onChange(local);
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="col-span-2 space-y-1">
        <Label>Name</Label>
        <Input
          value={local.name}
          disabled={disabled}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            updateLocal("name", e.target.value)
          }
          onBlur={commit}
        />
      </div>
      <div className="space-y-1">
        <Label>Attenuation (%)</Label>
        <Input
          type="number"
          value={local.attenuation_pct}
          disabled={disabled}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            updateLocal("attenuation_pct", e.target.value)
          }
          onBlur={commit}
        />
      </div>
      <div className="space-y-1">
        <Label>Temp range (°C)</Label>
        <div className="flex gap-2 items-center">
          <Input
            type="number"
            value={local.min_temp_c}
            disabled={disabled}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              updateLocal("min_temp_c", e.target.value)
            }
            onBlur={commit}
          />
          <span className="text-muted-foreground">–</span>
          <Input
            type="number"
            value={local.max_temp_c}
            disabled={disabled}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              updateLocal("max_temp_c", e.target.value)
            }
            onBlur={commit}
          />
        </div>
      </div>
    </div>
  );
}
