import { BASE_URL } from "./httpClient";
import { readSSEStream } from "./sse";

/**
 * Chat API (streaming)
 * Backend route: POST /chat  (Server-Sent Events)
 *
 * @param {string} query
 * @param {{role: "user"|"assistant", content: string}[]} [chat_history]
 * @param {string|null} [document_id]
 * @param {number|null} [top_k]
 * @param {object} handlers
 * @param {(status: {step: string, phase: string, message: string, detail?: object}) => void} [handlers.onStatus]
 * @param {(text: string) => void} [handlers.onToken] - text delta as it streams in
 * @param {(result: {answer: string, sources: object[]}) => void} [handlers.onDone]
 * @param {(detail: string) => void} [handlers.onError]
 */
export async function streamChatMessage(
  query,
  chat_history = [],
  document_id = null,
  top_k = null,
  { onStatus, onToken, onDone, onError } = {}
) {
  const payload = { query, chat_history };
  if (document_id !== null) payload.document_id = document_id;
  if (top_k !== null) payload.top_k = top_k;

  let response;
  try {
    response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    onError?.("Could not reach the server. Please check your connection.");
    return;
  }

  if (!response.ok) {
    let detail = "Something went wrong. Please try again.";
    try {
      const body = await response.json();
      detail = body?.detail || detail;
    } catch {
      // response wasn't JSON — keep the fallback message
    }
    onError?.(detail);
    return;
  }

  await readSSEStream(response, (eventName, data) => {
    if (eventName === "status") onStatus?.(data);
    else if (eventName === "token") onToken?.(data.text);
    else if (eventName === "done") onDone?.(data);
    else if (eventName === "error") onError?.(data.detail);
  });
}