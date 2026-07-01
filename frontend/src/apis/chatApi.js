import httpClient from "./httpClient";

/**
 * Chat API
 * Backend route: POST /chat
 */

/**
 * Send a chat message to the RAG backend and return the AI answer.
 *
 * @param {string} query - The user's question.
 * @param {string|null} [document_id] - Optionally restrict retrieval to a single document.
 * @param {number|null} [top_k] - Number of source chunks to retrieve (1–20).
 * @returns {Promise<{answer: string, sources: {text: string, source_file: string, score: number}[]}>}
 */
export async function sendChatMessage(query, document_id = null, top_k = null) {
  const payload = { query };
  if (document_id !== null) payload.document_id = document_id;
  if (top_k !== null) payload.top_k = top_k;

  const { data } = await httpClient.post("/chat", payload);
  return data;
}