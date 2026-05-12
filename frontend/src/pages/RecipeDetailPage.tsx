import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { StatsBar } from "@/components/StatsBar";
import { FermentablesTable } from "@/components/FermentablesTable";
import { HopsTable } from "@/components/HopsTable";
import { YeastCard } from "@/components/YeastCard";
import { ChatPanel } from "@/components/ChatPanel";
import { BrewNotesPanel } from "@/components/BrewNotesPanel";
import { SensoryProfileModal } from "@/components/SensoryProfileModal";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useRecipe, usePatchRecipe, useStyles } from "@/hooks/useRecipe";
import type { Fermentable, Hop, Yeast, RecipePatch } from "@/types/recipe";

export function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const recipeId = id!;

  const { data: recipe, isLoading, error } = useRecipe(recipeId);
  const patch = usePatchRecipe(recipeId);
  const { data: styles } = useStyles();
  const [profileOpen, setProfileOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="p-6 text-sm text-muted-foreground">Loading recipe…</div>
    );
  }

  if (error || !recipe) {
    return (
      <div className="p-6 text-sm text-destructive">
        {error instanceof Error ? error.message : "Recipe not found"}
      </div>
    );
  }

  function save<K extends keyof RecipePatch>(field: K, value: RecipePatch[K]) {
    patch.mutate({ [field]: value });
  }

  function handleFermentablesChange(fermentables: Fermentable[]) {
    patch.mutate({ fermentables });
  }

  function handleHopsChange(hops: Hop[]) {
    patch.mutate({ hops });
  }

  function handleYeastChange(yeast: Yeast) {
    patch.mutate({ yeast });
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-background flex flex-col">
        <header className="border-b px-6 py-3 flex items-center justify-between">
          <Link to="/" className={buttonVariants({ variant: "ghost" })}>
            ← My Recipes
          </Link>
          <h1 className="font-semibold truncate max-w-xs">{recipe.name}</h1>
          <Button variant="outline" onClick={() => setProfileOpen(true)}>
            Profile
          </Button>
        </header>

        <div className="flex-1 flex overflow-hidden">
          {/* Chat panel */}
          <div className="w-2/5 border-r flex flex-col p-4 min-h-0">
            <ChatPanel recipeId={recipeId} />
          </div>

          {/* Recipe panel */}
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            {/* Basic fields */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Name</Label>
                <Input
                  defaultValue={recipe.name}
                  onBlur={(e: React.FocusEvent<HTMLInputElement>) => save("name", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label>Batch size (L)</Label>
                <Input
                  type="number"
                  defaultValue={recipe.batch_size_liters}
                  onBlur={(e: React.FocusEvent<HTMLInputElement>) =>
                    save("batch_size_liters", parseFloat(e.target.value))
                  }
                />
              </div>
              <div className="col-span-2 space-y-1">
                <Label>Style</Label>
                <Select
                  defaultValue={recipe.style}
                  onValueChange={(val: string | null) => val && save("style", val)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select style" />
                  </SelectTrigger>
                  <SelectContent>
                    {styles?.map((s) => (
                      <SelectItem key={s.name} value={s.name}>
                        {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator />

            {/* Calculated stats */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Stats
              </p>
              <StatsBar stats={recipe.calculated} />
            </div>

            <Separator />

            {/* Fermentables */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Fermentables
              </p>
              <FermentablesTable
                fermentables={recipe.fermentables}
                onChange={handleFermentablesChange}
                disabled={patch.isPending}
              />
            </div>

            <Separator />

            {/* Hops */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Hops
              </p>
              <HopsTable
                hops={recipe.hops}
                onChange={handleHopsChange}
                disabled={patch.isPending}
              />
            </div>

            <Separator />

            {/* Yeast */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Yeast
              </p>
              <YeastCard
                yeast={recipe.yeast}
                onChange={handleYeastChange}
                disabled={patch.isPending}
              />
            </div>

            <Separator />

            {/* Brew notes */}
            <BrewNotesPanel recipeId={recipeId} />
          </div>
        </div>
      </div>

      <SensoryProfileModal
        recipeId={recipeId}
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
      />
    </ErrorBoundary>
  );
}
