import httpClient from "./httpClient";

/**
 * Chat session API
 * Backend routes: GET /sessions, GET /sessions/{id}/messages,
 * PATCH /sessions/{id}, DELETE /sessions/{id}
 */

export async function listSessions() {
  const { data } = await httpClient.get("/sessions");
  return data; // ChatSessionSummary[]
}

export async function getSessionMessages(sessionId) {
  const { data } = await httpClient.get(`/sessions/${sessionId}/messages`);
  return data; // ChatMessageOut[]
}

export async function renameSession(sessionId, title) {
  const { data } = await httpClient.patch(`/sessions/${sessionId}`, { title });
  return data;
}

export async function deleteSession(sessionId) {
  await httpClient.delete(`/sessions/${sessionId}`);
}