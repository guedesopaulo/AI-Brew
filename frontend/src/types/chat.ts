export interface ChatRequest {
  recipe_id: string;
  message: string;
  session_id: string;
}

export type SSEEventType = "token" | "tool_call" | "done" | "error";

export interface SSEEvent {
  event: SSEEventType;
  data: string;
}

export interface ToolCallPayload {
  name: string;
  input: Record<string, unknown>;
}

export type ChatStatus = "idle" | "streaming" | "done" | "error";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
