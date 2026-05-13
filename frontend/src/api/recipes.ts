import { apiFetch } from "./client";
import type {
  Recipe,
  RecipeWithStats,
  RecipePatch,
  BrewNotes,
  Style,
  SensoryProfile,
} from "@/types/recipe";

export async function getRecipes(): Promise<RecipeWithStats[]> {
  return apiFetch<RecipeWithStats[]>("/recipes");
}

export async function getRecipe(id: string): Promise<RecipeWithStats> {
  return apiFetch<RecipeWithStats>(`/recipe/${id}`);
}

export async function createRecipe(recipe: Recipe): Promise<{ id: string }> {
  return apiFetch<{ id: string }>("/recipe", {
    method: "POST",
    body: JSON.stringify(recipe),
  });
}

export async function patchRecipe(
  id: string,
  patch: RecipePatch,
): Promise<RecipeWithStats> {
  return apiFetch<RecipeWithStats>(`/recipe/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function getRecipeNotes(id: string): Promise<BrewNotes> {
  return apiFetch<BrewNotes>(`/recipe/${id}/notes`);
}

export async function getStyles(): Promise<Style[]> {
  return apiFetch<Style[]>("/recipes/styles");
}

export async function getSensoryProfile(id: string): Promise<SensoryProfile> {
  return apiFetch<SensoryProfile>(`/recipe/${id}/profile`);
}

export async function deleteRecipe(id: string): Promise<void> {
  await apiFetch<void>(`/recipe/${id}`, { method: "DELETE" });
}
