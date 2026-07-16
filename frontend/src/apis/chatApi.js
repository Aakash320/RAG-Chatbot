import { BASE_URL, getAccessToken } from "./httpClient";
import { readSSEStream } from "./sse";
import { refresh as refreshAuth } from "./authApi";

/**
 * Chat API (streaming)
 * Backend route: POST /chat  (Server-Sent Events)
 *
 * Uses raw fetch() rather than the axios instance because axios can't
 * expose a streaming response body the way SSE needs — so the bearer
 * token has to be attached manually here, and a 401 (expired access
 * token mid-session) is handled with the same one-retry pattern as the
 * axios interceptor in httpClient.js.
 *
 * @param {string} query
 * @param {string|null} [sessionId] - continue an existing session; omit/null to start a new one
 * @param {string|null} [document_id]
 * @param {number|null} [top_k]
 * @param {object} handlers
 * @param {(info: {session_id: string, title: string|null}) => void} [handlers.onSession] - fires first, always
 * @param {(status: {step: string, phase: string, message: string, detail?: object}) => void} [handlers.onStatus]
 * @param {(text: string) => void} [handlers.onToken]
 * @param {(result: {answer: string, sources: object[]}) => void} [handlers.onDone]
 * @param {(detail: string) => void} [handlers.onError]
 */
export async function streamChatMessage(
  query,
  sessionId = null,
  document_id = null,
  top_k = null,
  { onSession, onStatus, onToken, onDone, onError } = {}
) {
  const payload = { query };
  if (sessionId) payload.session_id = sessionId;
  if (document_id !== null) payload.document_id = document_id;
  if (top_k !== null) payload.top_k = top_k;

  const doFetch = (token) =>
    fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });

  let response;
  try {
    response = await doFetch(getAccessToken());

    if (response.status === 401) {
      try {
        await refreshAuth();
      } catch {
        onError?.("Your session has expired. Please sign in again.");
        return;
      }
      response = await doFetch(getAccessToken());
    }
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
    if (eventName === "session") onSession?.(data);
    else if (eventName === "status") onStatus?.(data);
    else if (eventName === "token") onToken?.(data.text);
    else if (eventName === "done") onDone?.(data);
    else if (eventName === "error") onError?.(data.detail);
  });
}