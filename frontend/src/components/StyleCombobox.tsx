import { useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { Style } from "@/types/recipe";

interface StyleComboboxProps {
  value: string;
  onChange: (value: string) => void;
  styles: Style[];
  disabled?: boolean;
}

export function StyleCombobox({ value, onChange, styles, disabled }: StyleComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const filtered = query
    ? styles.filter((s) => s.name.toLowerCase().includes(query.toLowerCase()))
    : styles;

  function handleSelect(name: string) {
    onChange(name);
    setQuery("");
    setOpen(false);
  }

  function handleBlur(e: React.FocusEvent<HTMLDivElement>) {
    if (!containerRef.current?.contains(e.relatedTarget as Node)) {
      setOpen(false);
      setQuery("");
    }
  }

  return (
    <div ref={containerRef} className="relative" onBlur={handleBlur}>
      <input
        className={cn(
          "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1",
          "text-sm shadow-xs outline-none placeholder:text-muted-foreground",
          "focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-ring",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
        placeholder="Select a style…"
        value={open ? query : value}
        disabled={disabled}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => setQuery(e.target.value)}
      />
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-border bg-popover shadow-md">
          <ul className="max-h-60 overflow-y-auto py-1 text-sm">
            {filtered.length === 0 && (
              <li className="px-3 py-2 text-muted-foreground">No styles found.</li>
            )}
            {filtered.map((s) => (
              <li key={s.name}>
                <button
                  type="button"
                  className={cn(
                    "w-full px-3 py-1.5 text-left hover:bg-accent hover:text-accent-foreground",
                    s.name === value && "font-medium text-primary",
                  )}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handleSelect(s.name)}
                >
                  {s.name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
