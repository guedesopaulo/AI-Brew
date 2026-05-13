import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useRecipeNotes } from "@/hooks/useRecipe";

interface BrewNotesPanelProps {
  recipeId: string;
}

export function BrewNotesPanel({ recipeId }: BrewNotesPanelProps) {
  const { data } = useRecipeNotes(recipeId);
  const content = data?.content ?? "";

  if (!content) return null;

  return (
    <Accordion>
      <AccordionItem value="brew-notes">
        <AccordionTrigger className="text-sm font-medium">
          Brew Notes
        </AccordionTrigger>
        <AccordionContent>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
