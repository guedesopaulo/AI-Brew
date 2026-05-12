import { Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { StatsBar } from "./StatsBar";
import type { RecipeWithStats } from "@/types/recipe";

interface RecipeCardProps {
  recipe: RecipeWithStats;
}

export function RecipeCard({ recipe }: RecipeCardProps) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle className="text-lg">{recipe.name}</CardTitle>
        <p className="text-sm text-muted-foreground">{recipe.style}</p>
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
