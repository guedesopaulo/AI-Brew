import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getRecipe,
  getRecipes,
  patchRecipe,
  createRecipe,
  deleteRecipe,
  getRecipeNotes,
  getStyles,
  getSensoryProfile,
} from "@/api/recipes";
import type { RecipePatch, Recipe } from "@/types/recipe";

export function useRecipes() {
  return useQuery({
    queryKey: ["recipes"],
    queryFn: getRecipes,
  });
}

export function useRecipe(id: string) {
  return useQuery({
    queryKey: ["recipe", id],
    queryFn: () => getRecipe(id),
    enabled: !!id,
  });
}

export function usePatchRecipe(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch: RecipePatch) => patchRecipe(id, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["recipe", id] });
      void queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });
}

export function useCreateRecipe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recipe: Recipe) => createRecipe(recipe),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });
}

export function useRecipeNotes(id: string) {
  return useQuery({
    queryKey: ["recipe-notes", id],
    queryFn: () => getRecipeNotes(id),
    enabled: !!id,
  });
}

export function useStyles() {
  return useQuery({
    queryKey: ["styles"],
    queryFn: getStyles,
    staleTime: Infinity,
  });
}

export function useDeleteRecipe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteRecipe(id),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: ["recipes"] });
      queryClient.removeQueries({ queryKey: ["recipe", id] });
    },
  });
}

export function useSensoryProfile(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["sensory-profile", id],
    queryFn: () => getSensoryProfile(id),
    enabled: enabled && !!id,
  });
}
