import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ToolCallsLog } from "./ToolCallsLog";
import { useChat } from "@/hooks/useChat";
import { useSession } from "@/hooks/useSession";
import { cn } from "@/lib/utils";

interface ChatPanelProps {
  recipeId: string;
}

export function ChatPanel({ recipeId }: ChatPanelProps) {
  const sessionId = useSession(recipeId);
  const { messages, toolCalls, status, send } = useChat(recipeId);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || status === "streaming") return;
    setInput("");
    await send(text, sessionId);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex-1 overflow-y-auto space-y-3 min-h-0">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground text-center pt-8">
            Ask me anything about your recipe.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "rounded-lg p-3 text-sm",
              msg.role === "user"
                ? "bg-primary text-primary-foreground ml-8 whitespace-pre-wrap"
                : "bg-muted mr-8",
            )}
          >
            {msg.role === "assistant" ? (
              <>
                <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-headings:my-1">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
                {status === "streaming" && i === messages.length - 1 && (
                  <span className="inline-block w-1 h-3 bg-current animate-pulse ml-1" />
                )}
              </>
            ) : (
              msg.content
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <ToolCallsLog toolCalls={toolCalls} />

      <div className="flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What do you want to brew? (Enter to send)"
          className="resize-none"
          rows={2}
          disabled={status === "streaming"}
        />
        <Button
          onClick={() => void handleSend()}
          disabled={status === "streaming" || !input.trim()}
          className="self-end"
        >
          Send
        </Button>
      </div>
    </div>
  );
}
