import { useState, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { X } from "lucide-react";
import type { Hop } from "@/types/recipe";

interface HopsTableProps {
  hops: Hop[];
  onChange: (hops: Hop[]) => void;
  disabled?: boolean;
}

export function HopsTable({ hops, onChange, disabled }: HopsTableProps) {
  const [local, setLocal] = useState<Hop[]>(hops);

  useEffect(() => {
    setLocal(hops);
  }, [hops]);

  function updateLocal(index: number, field: keyof Hop, value: string) {
    const numFields: (keyof Hop)[] = ["amount_g", "alpha_pct", "time_min"];
    setLocal((prev) =>
      prev.map((h, i) =>
        i !== index
          ? h
          : {
              ...h,
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
      { name: "Cascade", amount_g: 30, alpha_pct: 5.5, time_min: 60, use: "boil" as Hop["use"] },
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
            <TableHead>Amount (g)</TableHead>
            <TableHead>Alpha (%)</TableHead>
            <TableHead>Time (min)</TableHead>
            <TableHead>Use</TableHead>
            <TableHead className="w-8" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {local.map((h, i) => (
            <TableRow key={i}>
              <TableCell>
                <Input
                  value={h.name}
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
                  value={h.amount_g}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    updateLocal(i, "amount_g", e.target.value)
                  }
                  onBlur={commit}
                />
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  step="0.1"
                  value={h.alpha_pct}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    updateLocal(i, "alpha_pct", e.target.value)
                  }
                  onBlur={commit}
                />
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  value={h.time_min}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    updateLocal(i, "time_min", e.target.value)
                  }
                  onBlur={commit}
                />
              </TableCell>
              <TableCell>
                <Select
                  value={h.use}
                  disabled={disabled}
                  onValueChange={(val: string | null) => {
                    if (!val) return;
                    const updated = local.map((hop, idx) =>
                      idx === i ? { ...hop, use: val as Hop["use"] } : hop,
                    );
                    setLocal(updated);
                    onChange(updated);
                  }}
                >
                  <SelectTrigger className="w-28">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="boil">Boil</SelectItem>
                    <SelectItem value="whirlpool">Whirlpool</SelectItem>
                    <SelectItem value="dry-hop">Dry hop</SelectItem>
                  </SelectContent>
                </Select>
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
