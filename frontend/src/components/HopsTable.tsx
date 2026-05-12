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
  function update(index: number, field: keyof Hop, value: string) {
    const updated = hops.map((h, i) => {
      if (i !== index) return h;
      const numFields: (keyof Hop)[] = ["amount_g", "alpha_pct", "time_min"];
      return {
        ...h,
        [field]: numFields.includes(field) ? parseFloat(value) || 0 : value,
      };
    });
    onChange(updated);
  }

  function remove(index: number) {
    onChange(hops.filter((_, i) => i !== index));
  }

  function add() {
    onChange([
      ...hops,
      { name: "Cascade", amount_g: 30, alpha_pct: 5.5, time_min: 60, use: "boil" },
    ]);
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
          {hops.map((h, i) => (
            <TableRow key={i}>
              <TableCell>
                <Input
                  value={h.name}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => update(i, "name", e.target.value)}
                  onBlur={() => onChange(hops)}
                />
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  value={h.amount_g}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => update(i, "amount_g", e.target.value)}
                  onBlur={() => onChange(hops)}
                />
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  step="0.1"
                  value={h.alpha_pct}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => update(i, "alpha_pct", e.target.value)}
                  onBlur={() => onChange(hops)}
                />
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  value={h.time_min}
                  disabled={disabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => update(i, "time_min", e.target.value)}
                  onBlur={() => onChange(hops)}
                />
              </TableCell>
              <TableCell>
                <Select
                  value={h.use}
                  disabled={disabled}
                  onValueChange={(val: string | null) => {
                    if (!val) return;
                    update(i, "use", val);
                    onChange(hops.map((hop, idx) => (idx === i ? { ...hop, use: val as Hop["use"] } : hop)));
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
