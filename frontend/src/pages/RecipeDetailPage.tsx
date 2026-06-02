import { useState, useRef, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen, Trash2 } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { StyleCombobox } from "@/components/StyleCombobox";
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

const CHAT_MIN_PCT = 20;
const CHAT_MAX_PCT = 65;
const CHAT_DEFAULT_PCT = 40;

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
  const selectedStyle = styles?.find((s) => s.name === recipe?.style);

  const [chatWidth, setChatWidth] = useState(CHAT_DEFAULT_PCT);
  const [chatVisible, setChatVisible] = useState(true);
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setChatWidth(Math.max(CHAT_MIN_PCT, Math.min(CHAT_MAX_PCT, pct)));
    }
    function onMouseUp() {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

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
      <div className="h-screen bg-background flex flex-col">
        <header className="border-b px-6 py-3 flex items-center justify-between gap-2">
          <Link to="/" className={buttonVariants({ variant: "ghost" })}>
            ← My Recipes
          </Link>
          <h1 className="font-semibold truncate flex-1 text-center">
            {recipe.name}
          </h1>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setChatVisible((v) => !v)}
              title={chatVisible ? "Hide chat" : "Show chat"}
            >
              {chatVisible ? (
                <PanelLeftClose className="h-4 w-4 text-muted-foreground" />
              ) : (
                <PanelLeftOpen className="h-4 w-4 text-muted-foreground" />
              )}
            </Button>
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

        <div ref={containerRef} className="flex-1 flex overflow-hidden">
          {/* Chat panel */}
          <div
            className="flex flex-col min-h-0 overflow-hidden transition-[width] duration-150"
            style={{ width: chatVisible ? `${chatWidth}%` : "0" }}
          >
            <div className="flex flex-col h-full p-4 min-h-0">
              <ChatPanel recipeId={recipeId} />
            </div>
          </div>

          {/* Drag handle */}
          {chatVisible && (
            <div
              className="w-1.5 shrink-0 hover:bg-primary/30 cursor-col-resize flex items-center justify-center group transition-colors border-r border-border"
              onMouseDown={(e) => {
                isDragging.current = true;
                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
                e.preventDefault();
              }}
            >
              <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="w-0.5 h-0.5 rounded-full bg-muted-foreground" />
                ))}
              </div>
            </div>
          )}

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
                  key={recipe.batch_size_liters}
                  type="number"
                  defaultValue={recipe.batch_size_liters}
                  onBlur={(e: React.FocusEvent<HTMLInputElement>) =>
                    save("batch_size_liters", parseFloat(e.target.value))
                  }
                />
              </div>
              <div className="col-span-2 space-y-1">
                <Label>Style</Label>
                <StyleCombobox
                  value={recipe.style}
                  onChange={(val) => save("style", val)}
                  styles={styles ?? []}
                  disabled={patch.isPending}
                />
                {selectedStyle && (
                  <p className="text-xs text-muted-foreground">
                    OG {selectedStyle.og_min.toFixed(3)}–{selectedStyle.og_max.toFixed(3)}
                    {" · "}IBU {selectedStyle.ibu_min}–{selectedStyle.ibu_max}
                    {" · "}ABV {selectedStyle.abv_min}–{selectedStyle.abv_max}%
                    {" · "}SRM {selectedStyle.srm_min}–{selectedStyle.srm_max}
                  </p>
                )}
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
              <StatsBar stats={recipe.calculated} style={selectedStyle} />
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
