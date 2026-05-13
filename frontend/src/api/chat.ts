import { streamSSE } from "@/lib/sse";
import { apiFetch, apiToken } from "./client";
import type { ChatMessage, ChatRequest, SSEEvent } from "@/types/chat";

export function streamChat(request: ChatRequest): AsyncGenerator<SSEEvent> {
  return streamSSE("/api/chat", request, apiToken());
}

export async function getChatHistory(
  recipeId: string,
  sessionId: string,
): Promise<ChatMessage[]> {
  const data = await apiFetch<Array<{ role: string; content: string }>>(
    `/recipe/${recipeId}/history?session_id=${encodeURIComponent(sessionId)}`,
  );
  return data.map((m) => ({
    role: m.role as "user" | "assistant",
    content: m.content,
  }));
}
