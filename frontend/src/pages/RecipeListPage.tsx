import { useNavigate } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";
import { Button } from "@/components/ui/button";
import { RecipeCard } from "@/components/RecipeCard";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useRecipes, useCreateRecipe } from "@/hooks/useRecipe";

export function RecipeListPage() {
  const { data: recipes, isLoading, error } = useRecipes();
  const createRecipe = useCreateRecipe();
  const navigate = useNavigate();

  async function handleNew() {
    const id = uuidv4();
    await createRecipe.mutateAsync({
      id,
      name: "New Recipe",
      style: "American IPA",
      batch_size_liters: 20,
      fermentables: [],
      hops: [],
      yeast: {
        name: "SafAle US-05",
        attenuation_pct: 78,
        min_temp_c: 15,
        max_temp_c: 24,
      },
    });
    navigate(`/recipe/${id}`);
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-background">
        <header className="border-b px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">BrewAgent</h1>
          <Button onClick={() => void handleNew()} disabled={createRecipe.isPending}>
            + New Recipe
          </Button>
        </header>

        <main className="px-6 py-6">
          {isLoading && (
            <p className="text-sm text-muted-foreground">Loading recipes…</p>
          )}
          {error && (
            <p className="text-sm text-destructive">
              {error instanceof Error ? error.message : String(error)}
            </p>
          )}
          {recipes && recipes.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-16">
              No recipes yet. Start by clicking &ldquo;+ New Recipe&rdquo;.
            </p>
          )}
          {recipes && recipes.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {recipes.map((r) => (
                <RecipeCard key={r.id} recipe={r} />
              ))}
            </div>
          )}
        </main>
      </div>
    </ErrorBoundary>
  );
}
