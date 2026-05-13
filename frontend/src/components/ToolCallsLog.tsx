import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import type { ToolCallPayload } from "@/types/chat";

interface ToolCallsLogProps {
  toolCalls: ToolCallPayload[];
}

export function ToolCallsLog({ toolCalls }: ToolCallsLogProps) {
  if (toolCalls.length === 0) return null;

  return (
    <Accordion>
      <AccordionItem value="tool-calls">
        <AccordionTrigger className="text-sm text-muted-foreground">
          Tool calls ({toolCalls.length})
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-1 font-mono text-xs">
            {toolCalls.map((tc, i) => (
              <div key={i} className="bg-muted rounded p-2">
                <span className="font-semibold">{tc.name}</span>{" "}
                <span className="text-muted-foreground">
                  {JSON.stringify(tc.input)}
                </span>
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
