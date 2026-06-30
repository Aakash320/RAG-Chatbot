import React, { useState } from "react";
import { Table, Tag, Button, Popconfirm, message, Typography } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import { deleteDocument } from "../../apis/documentApi";

const { Text } = Typography;

const statusColors = {
  processing: "blue",
  ready: "green",
  failed: "red",
};

function formatBytes(bytes) {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * DocumentList renders ingested documents in a table with a delete action.
 * `documents` items are expected to look like:
 * { id, name, status, sizeBytes, createdAt }
 */
export default function DocumentList({ documents, onDeleted, loading }) {
  const [deletingId, setDeletingId] = useState(null);

  const handleDelete = async (record) => {
    setDeletingId(record.id);
    try {
      // TODO: deleteDocument() in apis/documentApi.js is currently a placeholder.
      await deleteDocument(record.id);
      message.success(`${record.name} deleted`);
      onDeleted?.(record.id);
    } catch (error) {
      message.error(`Failed to delete ${record.name}`);
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (name) => <Text strong>{name}</Text>,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 140,
      render: (status) => (
        <Tag color={statusColors[status] ?? "default"}>{status ?? "unknown"}</Tag>
      ),
    },
    {
      title: "Size",
      dataIndex: "sizeBytes",
      key: "sizeBytes",
      width: 120,
      render: formatBytes,
    },
    {
      title: "Uploaded",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 200,
      render: (value) => (value ? new Date(value).toLocaleString() : "—"),
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
            loading={deletingId === record.id}
          />
        </Popconfirm>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
      dataSource={documents}
      loading={loading}
      pagination={{ pageSize: 10 }}
    />
  );
}
