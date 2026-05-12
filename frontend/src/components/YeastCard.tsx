import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Yeast } from "@/types/recipe";

interface YeastCardProps {
  yeast: Yeast;
  onChange: (yeast: Yeast) => void;
  disabled?: boolean;
}

export function YeastCard({ yeast, onChange, disabled }: YeastCardProps) {
  function update(field: keyof Yeast, value: string) {
    const numFields: (keyof Yeast)[] = [
      "attenuation_pct",
      "min_temp_c",
      "max_temp_c",
    ];
    onChange({
      ...yeast,
      [field]: numFields.includes(field) ? parseFloat(value) || 0 : value,
    });
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="col-span-2 space-y-1">
        <Label>Name</Label>
        <Input
          value={yeast.name}
          disabled={disabled}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => update("name", e.target.value)}
          onBlur={() => onChange(yeast)}
        />
      </div>
      <div className="space-y-1">
        <Label>Attenuation (%)</Label>
        <Input
          type="number"
          value={yeast.attenuation_pct}
          disabled={disabled}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => update("attenuation_pct", e.target.value)}
          onBlur={() => onChange(yeast)}
        />
      </div>
      <div className="space-y-1">
        <Label>Temp range (°C)</Label>
        <div className="flex gap-2 items-center">
          <Input
            type="number"
            value={yeast.min_temp_c}
            disabled={disabled}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => update("min_temp_c", e.target.value)}
            onBlur={() => onChange(yeast)}
          />
          <span className="text-muted-foreground">–</span>
          <Input
            type="number"
            value={yeast.max_temp_c}
            disabled={disabled}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => update("max_temp_c", e.target.value)}
            onBlur={() => onChange(yeast)}
          />
        </div>
      </div>
    </div>
  );
}
