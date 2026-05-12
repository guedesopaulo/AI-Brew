import { streamSSE } from "@/lib/sse";
import { apiToken } from "./client";
import type { ChatRequest, SSEEvent } from "@/types/chat";

export function streamChat(request: ChatRequest): AsyncGenerator<SSEEvent> {
  return streamSSE("/api/chat", request, apiToken());
}
