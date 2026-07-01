import React, { useEffect, useState } from "react";
import { Card, Typography, message } from "antd";
import DocumentUploader from "../components/document/DocumentUploader";
import DocumentList from "../components/document/DocumentList";
import { listDocuments } from "../apis/documentApi";
import { getErrorMessage } from "../apis/httpClient";

const { Title, Paragraph } = Typography;

export default function DocumentPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const { documents: docs } = await listDocuments();
      setDocuments(docs ?? []);
    } catch (error) {
      message.error(getErrorMessage(error, "Failed to load documents"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleIngested = (record) => {
    // Optimistically add the new document to the top of the list.
    // Alternative: fetchDocuments() to refetch instead.
    setDocuments((prev) => [record, ...prev]);
  };

  const handleDeleted = (documentId) => {
    setDocuments((prev) => prev.filter((doc) => doc.document_id !== documentId));
  };

  return (
    <>
      <Card style={{ borderRadius: 0 }}>
        <Title level={5}>Ingest a document</Title>
        <Paragraph type="secondary">
          Upload files to make them searchable by the chat assistant.
        </Paragraph>
        <DocumentUploader onIngested={handleIngested} />
      </Card>

      <Card style={{ borderRadius: 0, border: "none" }}>
        <Title level={5}>Ingested documents</Title>
        <DocumentList documents={documents} onDeleted={handleDeleted} loading={loading} />
      </Card>
    </>
  );
}