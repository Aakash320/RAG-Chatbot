import httpClient from "./httpClient";

/**
 * Document API
 * Backend routes: GET /document, POST /document, DELETE /document
 */

/**
 * List ingested documents.
 * TODO: replace this placeholder with the real implementation, e.g.:
 *
 * export async function listDocuments(params) {
 *   const { data } = await httpClient.get("/document", { params });
 *   return data;
 * }
 *
 * Expected response shape (suggested):
 * {
 *   documents: [
 *     { id: string, name: string, status: "processing" | "ready" | "failed",
 *       sizeBytes: number, createdAt: string }
 *   ]
 * }
 */
export async function listDocuments(params) {
  // PLACEHOLDER: no real API call yet.
  console.warn("[apis/document] listDocuments() is a placeholder — wire up GET /document");
  return Promise.resolve({ documents: [] });
}

/**
 * Ingest (upload) a new document.
 * TODO: replace this placeholder with the real implementation, e.g.:
 *
 * export async function ingestDocument(file, onUploadProgress) {
 *   const formData = new FormData();
 *   formData.append("file", file);
 *   const { data } = await httpClient.post("/document", formData, {
 *     headers: { "Content-Type": "multipart/form-data" },
 *     onUploadProgress,
 *   });
 *   return data;
 * }
 */
export async function ingestDocument(file, onUploadProgress) {
  // PLACEHOLDER: simulate a network delay instead of a real upload.
  console.warn("[apis/document] ingestDocument() is a placeholder — wire up POST /document");
  await new Promise((resolve) => setTimeout(resolve, 800));
  return {
    id: `placeholder-${Date.now()}`,
    name: file?.name ?? "untitled",
    status: "processing",
    sizeBytes: file?.size ?? 0,
    createdAt: new Date().toISOString(),
  };
}

/**
 * Delete a document by id.
 * TODO: replace this placeholder with the real implementation, e.g.:
 *
 * export async function deleteDocument(documentId) {
 *   const { data } = await httpClient.delete(`/document/${documentId}`);
 *   return data;
 * }
 */
export async function deleteDocument(documentId) {
  // PLACEHOLDER: no real API call yet.
  console.warn("[apis/document] deleteDocument() is a placeholder — wire up DELETE /document");
  return Promise.resolve({ id: documentId, deleted: true });
}
