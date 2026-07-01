import React, { useState } from "react";
import { Table, Button, Popconfirm, message, Typography } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import { deleteDocument } from "../../apis/documentApi";
import { getErrorMessage } from "../../apis/httpClient";

const { Text } = Typography;

/**
 * DocumentList renders ingested documents in a table with a delete action.
 * `documents` items match the backend's DocumentMetadata shape exactly:
 * { document_id, filename, file_type, chunk_count }
 */
export default function DocumentList({ documents, onDeleted, loading }) {
  const [deletingId, setDeletingId] = useState(null);

  const handleDelete = async (record) => {
    setDeletingId(record.document_id);
    try {
      await deleteDocument(record.document_id);
      message.success(`${record.filename} deleted`);
      onDeleted?.(record.document_id);
    } catch (error) {
      message.error(getErrorMessage(error, `Failed to delete ${record.filename}`));
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    {
      title: "Name",
      dataIndex: "filename",
      key: "filename",
      render: (filename) => <Text strong>{filename}</Text>,
    },
    {
      title: "Type",
      dataIndex: "file_type",
      key: "file_type",
      width: 100,
    },
    {
      title: "Chunks",
      dataIndex: "chunk_count",
      key: "chunk_count",
      width: 100,
      render: (count) => (count != null ? count : "—"),
    },
    {
      title: "",
      key: "actions",
      width: 80,
      render: (_, record) => (
        <Popconfirm
          title="Delete this document?"
          description="This cannot be undone."
          okText="Delete"
          okButtonProps={{ danger: true }}
          onConfirm={() => handleDelete(record)}
        >
          <Button
            danger
            type="text"
            icon={<DeleteOutlined />}
            loading={deletingId === record.document_id}
          />
        </Popconfirm>
      ),
    },
  ];

  return (
    <Table
      rowKey="document_id"
      columns={columns}
      dataSource={documents}
      loading={loading}
      pagination={{ pageSize: 10 }}
    />
  );
}