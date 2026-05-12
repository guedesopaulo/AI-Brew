import { useState, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { streamChat } from "@/api/chat";
import type { ChatMessage, ChatStatus, ToolCallPayload } from "@/types/chat";

interface UseChatReturn {
  messages: ChatMessage[];
  toolCalls: ToolCallPayload[];
  status: ChatStatus;
  send: (message: string, recipeId: string, sessionId: string) => Promise<void>;
}

export function useChat(_recipeId: string): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallPayload[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const queryClient = useQueryClient();
  const abortRef = useRef<boolean>(false);

  const send = useCallback(
    async (message: string, recipeId: string, sessionId: string) => {
      abortRef.current = false;
      setStatus("streaming");
      setMessages((prev) => [
        ...prev,
        { role: "user", content: message },
        { role: "assistant", content: "" },
      ]);

      try {
        const stream = streamChat({
          recipe_id: _recipeId,
          message,
          session_id: sessionId,
        });

        for await (const { event, data } of stream) {
          if (abortRef.current) break;

          if (event === "token") {
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: updated[updated.length - 1].content + data,
              };
              return updated;
            });
          } else if (event === "tool_call") {
            try {
              const tc = JSON.parse(data) as ToolCallPayload;
              setToolCalls((prev) => [...prev, tc]);
            } catch {
              // ignore malformed tool_call events
            }
          } else if (event === "error") {
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: `Error: ${data}`,
              };
              return updated;
            });
            setStatus("error");
            return;
          } else if (event === "done") {
            break;
          }
        }

        // Refresh recipe and notes after agent completes
        void queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
        void queryClient.invalidateQueries({
          queryKey: ["recipe-notes", recipeId],
        });
        setStatus("done");
      } catch (err) {
        setMessages((prev) => {
          const updated = [...prev];
          if (updated.length > 0) {
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: `Error: ${err instanceof Error ? err.message : String(err)}`,
            };
          }
          return updated;
        });
        setStatus("error");
      }
    },
    [queryClient],
  );

  return { messages, toolCalls, status, send };
}
