import httpClient from "./httpClient";

/**
 * Document API
 * Backend routes: GET /documents, POST /documents, DELETE /documents/{document_id}
 *
 * All functions return the backend response body as-is — same field
 * names as the backend (document_id, filename, file_type, chunk_count).
 * No remapping/renaming happens here.
 */

/**
 * List ingested documents.
 * Backend response: { documents: [{ document_id, filename, file_type, chunk_count }], total }
 */
export async function listDocuments() {
  const { data } = await httpClient.get("/documents");
  return data;
}

/**
 * Ingest (upload) a new document.
 * Backend response: { document_id, filename, file_type, chunk_count }
 */
export async function ingestDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await httpClient.post("/documents", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/**
 * Delete a document by id.
 * Backend response: { document_id, deleted }
 */
export async function deleteDocument(documentId) {
  const { data } = await httpClient.delete(`/documents/${documentId}`);
  return data;
}