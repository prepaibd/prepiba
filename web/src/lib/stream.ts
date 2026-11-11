import { ApiError, authedFetch } from "./api";

export type ChatEvent =
  | { type: "delta"; text: string }
  | { type: "done"; message_id: string }
  | { type: "error"; detail: string };

/**
 * POST a tutor message and call `onEvent` for each server-sent event as it arrives.
 * Throws ApiError for HTTP-level failures (400/429/503...) that happen before streaming starts.
 */
export async function streamMessage(
  sessionId: string,
  content: string,
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await authedFetch(`/chat/sessions/${sessionId}/messages/`, { method: "POST", body: { content }, signal });
  if (!res.ok || !res.body) throw new ApiError(res.status, await res.json().catch(() => null));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let end: number;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      if (frame.startsWith("data: ")) {
        try { onEvent(JSON.parse(frame.slice(6)) as ChatEvent); } catch { /* ignore a malformed frame */ }
      }
    }
  }
}
