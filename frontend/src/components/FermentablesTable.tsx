import { useState, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { X } from "lucide-react";
import type { Fermentable } from "@/types/recipe";

interface FermentablesTableProps {
  fermentables: Fermentable[];
  onChange: (fermentables: Fermentable[]) => void;
  disabled?: boolean;
}

export function FermentablesTable({
  fermentables,
  onChange,
  disabled,
}: FermentablesTableProps) {
  const [local, setLocal] = useState<Fermentable[]>(fermentables);

  // Sync when the prop changes (e.g. agent patches the recipe)
  useEffect(() => {
    setLocal(fermentables);
  }, [fermentables]);

  function updateLocal(index: number, field: keyof Fermentable, value: string) {
    const numFields: (keyof Fermentable)[] = ["amount_kg", "color_ebc", "ppg"];
    setLocal((prev) =>
      prev.map((f, i) =>
        i !== index
          ? f
          : {
              ...f,
              [field]: numFields.includes(field) ? parseFloat(value) || 0 : value,
            },
      ),
    );
  }

  function commit() {
    onChange(local);
  }

  function remove(index: number) {
    const updated = local.filter((_, i) => i !== index);
    setLocal(updated);
    onChange(updated);
  }

  function add() {
    const updated = [
      ...local,
      { name: "New Malt", amount_kg: 1.0, color_ebc: 5, ppg: 37 },
    ];
    setLocal(updated);
    onChange(updated);
  }

  return (
    <div className="space-y-2">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Amount (kg)</TableHead>
            <TableHead>Color (EBC)</TableHead>
            <TableHead>PPG</TableHead>
            <TableHead className="w-8" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {local.map((f, i) => (
            <TableRow key={i}>
              <TableCell>
                <Input
                  value={f.name}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    updateLocal(i, "name", e.target.value)
                  }
                  onBlur={commit}
                />
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  step="0.1"
                  value={f.amount_kg}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    updateLocal(i, "amount_kg", e.target.value)
                  }
                  onBlur={commit}
                />
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  value={f.color_ebc}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    updateLocal(i, "color_ebc", e.target.value)
                  }
                  onBlur={commit}
                />
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  value={f.ppg}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    updateLocal(i, "ppg", e.target.value)
                  }
                  onBlur={commit}
                />
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={disabled}
                  onClick={() => remove(i)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Button variant="outline" size="sm" disabled={disabled} onClick={add}>
        + Add
      </Button>
    </div>
  );
}
