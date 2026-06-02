import { cn } from "@/lib/utils";
import type { CalculatedStats, Style } from "@/types/recipe";

interface StatsBarProps {
  stats: CalculatedStats;
  style?: Style;
}

function StatBar({
  label,
  value,
  min,
  max,
  format,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  format: (v: number) => string;
}) {
  const rangeSpan = max - min || 0.001;
  // Extend the display range to always include the current value
  const overshoot = Math.max(
    0,
    value < min ? min - value : value > max ? value - max : 0,
  );
  const pad = rangeSpan * 0.35 + overshoot;
  const displayMin = min - pad;
  const displayMax = max + pad;
  const displaySpan = displayMax - displayMin;

  const toPercent = (v: number) =>
    Math.max(0, Math.min(100, ((v - displayMin) / displaySpan) * 100));

  const rangeLeft = toPercent(min);
  const rangeWidth = toPercent(max) - rangeLeft;
  const markerPos = toPercent(value);
  const inRange = value >= min && value <= max;

  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-1">
        <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <span
          className={cn(
            "text-xs font-semibold tabular-nums",
            inRange ? "text-green-600" : "text-red-500",
          )}
        >
          {format(value)}
        </span>
      </div>
      {/* track */}
      <div className="relative h-2">
        <div className="absolute inset-0 rounded-full bg-muted" />
        {/* style range band */}
        <div
          className="absolute h-full rounded-full bg-blue-200 dark:bg-blue-800"
          style={{ left: `${rangeLeft}%`, width: `${rangeWidth}%` }}
        />
        {/* value marker */}
        <div
          className={cn(
            "absolute top-1/2 h-4 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-sm",
            inRange ? "bg-green-500" : "bg-red-500",
          )}
          style={{ left: `${markerPos}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] tabular-nums text-muted-foreground">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}

export function StatsBar({ stats, style }: StatsBarProps) {
  if (!style) {
    return (
      <div className="flex flex-wrap gap-2">
        {(
          [
            ["OG", stats.og.toFixed(3)],
            ["FG", stats.fg.toFixed(3)],
            ["ABV", `${stats.abv.toFixed(1)}%`],
            ["IBU", stats.ibu.toFixed(0)],
            ["SRM", stats.srm.toFixed(1)],
          ] as [string, string][]
        ).map(([label, val]) => (
          <span
            key={label}
            className="inline-flex items-center rounded-full border bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground"
          >
            {label} {val}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-5">
      <StatBar
        label="OG"
        value={stats.og}
        min={style.og_min}
        max={style.og_max}
        format={(v) => v.toFixed(3)}
      />
      <StatBar
        label="FG"
        value={stats.fg}
        min={style.fg_min}
        max={style.fg_max}
        format={(v) => v.toFixed(3)}
      />
      <StatBar
        label="ABV"
        value={stats.abv}
        min={style.abv_min}
        max={style.abv_max}
        format={(v) => `${v.toFixed(1)}%`}
      />
      <StatBar
        label="IBU"
        value={stats.ibu}
        min={style.ibu_min}
        max={style.ibu_max}
        format={(v) => v.toFixed(0)}
      />
      <StatBar
        label="SRM"
        value={stats.srm}
        min={style.srm_min}
        max={style.srm_max}
        format={(v) => v.toFixed(1)}
      />
    </div>
  );
}
