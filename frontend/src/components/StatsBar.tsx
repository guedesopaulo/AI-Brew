import { Badge } from "@/components/ui/badge";
import type { CalculatedStats } from "@/types/recipe";

interface StatsBarProps {
  stats: CalculatedStats;
}

export function StatsBar({ stats }: StatsBarProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <Badge variant="secondary">OG {stats.og.toFixed(3)}</Badge>
      <Badge variant="secondary">FG {stats.fg.toFixed(3)}</Badge>
      <Badge variant="secondary">ABV {stats.abv.toFixed(1)}%</Badge>
      <Badge variant="secondary">IBU {stats.ibu.toFixed(0)}</Badge>
      <Badge variant="secondary">SRM {stats.srm.toFixed(1)}</Badge>
    </div>
  );
}
