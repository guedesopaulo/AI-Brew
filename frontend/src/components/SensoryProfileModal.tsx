import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useSensoryProfile } from "@/hooks/useRecipe";

interface SensoryProfileModalProps {
  recipeId: string;
  open: boolean;
  onClose: () => void;
}

export function SensoryProfileModal({
  recipeId,
  open,
  onClose,
}: SensoryProfileModalProps) {
  const { data, isLoading, error } = useSensoryProfile(recipeId, open);

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sensory Profile</DialogTitle>
        </DialogHeader>
        {isLoading && (
          <p className="text-sm text-muted-foreground">
            Analysing recipe… this may take a moment.
          </p>
        )}
        {error && (
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : String(error)}
          </p>
        )}
        {data && (
          <div className="space-y-3">
            {(
              [
                ["Aroma", data.aroma],
                ["Flavor", data.flavor],
                ["Mouthfeel", data.mouthfeel],
                ["Appearance", data.appearance],
              ] as [string, string][]
            ).map(([label, value]) => (
              <div key={label}>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {label}
                </p>
                <p className="text-sm">{value}</p>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
