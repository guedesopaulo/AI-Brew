import { useState } from "react";
import { Link } from "react-router-dom";
import { Trash2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
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
import { StatsBar } from "./StatsBar";
import { useDeleteRecipe } from "@/hooks/useRecipe";
import type { RecipeWithStats } from "@/types/recipe";

interface RecipeCardProps {
  recipe: RecipeWithStats;
}

export function RecipeCard({ recipe }: RecipeCardProps) {
  const [open, setOpen] = useState(false);
  const deleteMutation = useDeleteRecipe();

  function handleDelete() {
    deleteMutation.mutate(recipe.id, {
      onSuccess: () => setOpen(false),
    });
  }

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle className="text-lg">{recipe.name}</CardTitle>
            <p className="text-sm text-muted-foreground">{recipe.style}</p>
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
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
      </CardHeader>
      <CardContent className="flex-1">
        <StatsBar stats={recipe.calculated} />
        <p className="text-sm text-muted-foreground mt-2">
          {recipe.batch_size_liters} L batch
        </p>
      </CardContent>
      <CardFooter>
        <Link
          to={`/recipe/${recipe.id}`}
          className={buttonVariants({ className: "w-full" })}
        >
          Open
        </Link>
      </CardFooter>
    </Card>
  );
}
