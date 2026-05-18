import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Trash2 } from "lucide-react";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import { StatsBar } from "@/components/StatsBar";
import { FermentablesTable } from "@/components/FermentablesTable";
import { HopsTable } from "@/components/HopsTable";
import { YeastCard } from "@/components/YeastCard";
import { ChatPanel } from "@/components/ChatPanel";
import { BrewNotesPanel } from "@/components/BrewNotesPanel";
import { SensoryProfileModal } from "@/components/SensoryProfileModal";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useRecipe, usePatchRecipe, useStyles, useDeleteRecipe } from "@/hooks/useRecipe";
import { EquipmentSelector } from "@/components/EquipmentSelector";
import type { Fermentable, Hop, Yeast, RecipePatch } from "@/types/recipe";

export function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const recipeId = id!;
  const navigate = useNavigate();

  const { data: recipe, isLoading, error } = useRecipe(recipeId);
  const patch = usePatchRecipe(recipeId);
  const deleteMutation = useDeleteRecipe();
  const { data: styles } = useStyles();
  const [profileOpen, setProfileOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

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

  function handleDelete() {
    deleteMutation.mutate(recipeId, {
      onSuccess: () => navigate("/"),
    });
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
        <header className="border-b px-6 py-3 flex items-center justify-between gap-2">
          <Link to="/" className={buttonVariants({ variant: "ghost" })}>
            ← My Recipes
          </Link>
          <h1 className="font-semibold truncate flex-1 text-center">
            {recipe.name}
          </h1>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setProfileOpen(true)}>
              Profile
            </Button>
            <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
              <DialogTrigger render={<Button variant="ghost" size="icon-sm" />}>
                <Trash2 className="h-4 w-4 text-muted-foreground" />
                <span className="sr-only">Delete recipe</span>
              </DialogTrigger>
              <DialogContent showCloseButton={false}>
                <DialogHeader>
                  <DialogTitle>Delete recipe?</DialogTitle>
                  <DialogDescription>
                    "{recipe.name}" will be permanently deleted. This cannot be
                    undone.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <DialogClose render={<Button variant="outline" />}>
                    Cancel
                  </DialogClose>
                  <Button
                    variant="destructive"
                    onClick={handleDelete}
                    disabled={deleteMutation.isPending}
                  >
                    {deleteMutation.isPending ? "Deleting…" : "Delete"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
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
              <div className="col-span-2">
                <EquipmentSelector
                  recipeId={recipeId}
                  currentEquipmentId={recipe.equipment_id}
                  disabled={patch.isPending}
                />
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
