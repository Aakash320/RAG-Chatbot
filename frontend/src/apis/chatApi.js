import httpClient from "./httpClient";

/**
 * Chat API
 * Backend route: POST /chat
 */

/**
 * Send a new chat message and get the AI's reply.
 * TODO: replace this placeholder with the real implementation, e.g.:
 *
 * export async function sendChatMessage(message) {
 *   const { data } = await httpClient.post("/chat", { message });
 *   return data;
 * }
 *
 * Expected response shape (suggested):
 * { id: string, role: "assistant", content: string, createdAt: string }
 */
export async function sendChatMessage(message) {
  // PLACEHOLDER: simulate a network delay and a canned AI response.
  console.warn("[apis/chat] sendChatMessage() is a placeholder — wire up POST /chat");
  await new Promise((resolve) => setTimeout(resolve, 600));
  return {
    id: `placeholder-${Date.now()}`,
    role: "assistant",
    content: "This is a placeholder AI response. Connect the real chat API to replace this.",
    createdAt: new Date().toISOString(),
  };
}
