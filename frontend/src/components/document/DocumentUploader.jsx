import React, { useState } from "react";
import { Upload, Button, message } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import { ingestDocument } from "../../apis/documentApi";

const { Dragger } = Upload;

/**
 * DocumentUploader handles picking/dropping a file and ingesting it.
 * Calls onIngested(documentRecord) after a successful upload.
 */
export default function DocumentUploader({ onIngested }) {
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (file) => {
    setUploading(true);
    try {
      // TODO: ingestDocument() in apis/documentApi.js is currently a placeholder.
      const record = await ingestDocument(file);
      message.success(`${file.name} ingested`);
      onIngested?.(record);
    } catch (error) {
      message.error(`${file.name} failed to ingest`);
    } finally {
      setUploading(false);
    }
    // Returning false tells antd's Upload not to perform its own
    // automatic XHR submission, since we're handling it manually above.
    return false;
  };

  return (
    <Dragger
      multiple
      showUploadList={false}
      beforeUpload={handleUpload}
      disabled={uploading}
    >
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">Click or drag a file to this area to ingest</p>
      <p className="ant-upload-hint">
        Supports single or bulk upload. Files will be processed and made available to the chat assistant.
      </p>
      <Button style={{ marginTop: 12 }} loading={uploading}>
        Select file
      </Button>
    </Dragger>
  );
}
