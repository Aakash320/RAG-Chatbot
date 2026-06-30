import React, { useEffect, useState } from "react";
import { Card, Space, Typography } from "antd";
import DocumentUploader from "../components/document/DocumentUploader";
import DocumentList from "../components/document/DocumentList";
import { listDocuments } from "../apis/documentApi";

const { Title, Paragraph } = Typography;

export default function DocumentPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      // TODO: listDocuments() in apis/documentApi.js is currently a placeholder.
      const { documents: docs } = await listDocuments();
      setDocuments(docs ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleIngested = (record) => {
    // Optimistically add the new document to the top of the list.
    // Once the real API is wired up, you may prefer to just refetch:
    // fetchDocuments();
    setDocuments((prev) => [record, ...prev]);
  };

  const handleDeleted = (id) => {
    setDocuments((prev) => prev.filter((doc) => doc.id !== id));
  };

  return (
    <>
      <Card style={{borderRadius: 0, border: "none"}}>
        <Title level={5}>Ingest a document</Title>
        <Paragraph type="secondary">
          Upload files to make them searchable by the chat assistant.
        </Paragraph>
        <DocumentUploader onIngested={handleIngested} />
      </Card>

      <Card style={{borderRadius: 0, border: "none"}}>
        <Title level={5}>Ingested documents</Title>
        <DocumentList
          documents={documents}
          onDeleted={handleDeleted}
          loading={loading}
        />
      </Card>
    </>
  );
}
