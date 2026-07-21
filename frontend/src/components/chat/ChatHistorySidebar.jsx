import React, { useState } from "react";
import {
  Button,
  Dropdown,
  Empty,
  Flex,
  Input,
  List,
  Modal,
  Spin,
  Typography,
  message,
} from "antd";
import {
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import { useChatHistory } from "../../context/ChatHistoryContext";
import { ROUTES } from "../../constants/routes";

const { Text } = Typography;

const menuItems = [
  {
    key: "rename",
    icon: <EditOutlined />,
    label: "Rename",
  },
  {
    key: "delete",
    icon: <DeleteOutlined />,
    label: "Delete",
    danger: true,
  },
];

/**
 * Chat history panel rendered inside the app's persistent sidebar.
 * Reads/writes the session list via ChatHistoryContext, and drives
 * navigation directly so it works from any page (chat, documents, profile).
 */
export default function ChatHistorySidebar() {
  const navigate = useNavigate();
  const { sessionId: activeSessionId } = useParams();
  const { sessions, loading, removeSession, renameSession } = useChatHistory();

  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");

  const handleNewChat = () => navigate(ROUTES.CHAT);
  const handleSelect = (sessionId) => navigate(`${ROUTES.CHAT}/${sessionId}`);

  const handleDelete = async (sessionId) => {
    await removeSession(sessionId);
    if (sessionId === activeSessionId) handleNewChat();
  };

  const handleSaveRename = async () => {
    if (!editingSessionId) return;
    const targetId = editingSessionId;
    const trimmed = editingTitle.trim();
    setEditingSessionId(null);

    if (!trimmed) return;
    const currentSession = sessions.find((s) => s.id === targetId);
    if (currentSession && currentSession.title === trimmed) return;

    try {
      await renameSession(targetId, trimmed);
      message.success("Session renamed");
    } catch (err) {
      message.error("Failed to rename session");
    }
  };

  const handleMenuClick = (key, session) => {
    if (key === "rename") {
      setEditingSessionId(session.id);
      setEditingTitle(session.title || "New conversation");
    } else if (key === "delete") {
      Modal.confirm({
        title: "Delete conversation?",
        content: "Are you sure you want to delete this chat session?",
        okText: "Delete",
        okType: "danger",
        cancelText: "Cancel",
        onOk: () => handleDelete(session.id),
      });
    }
  };

  return (
    <Flex vertical style={{ height: "100%", minHeight: 0 }}>
      <div style={{ padding: "0 12px 12px" }}>
        <Button icon={<PlusOutlined />} block onClick={handleNewChat}>
          New chat
        </Button>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: "0 8px" }}>
        {loading ? (
          <Flex justify="center" style={{ padding: 24 }}>
            <Spin />
          </Flex>
        ) : sessions.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No conversations yet"
            style={{ marginTop: 24 }}
          />
        ) : (
          <List
            dataSource={sessions}
            renderItem={(session) => (
              <List.Item
                key={session.id}
                onClick={() => {
                  if (editingSessionId !== session.id) {
                    handleSelect(session.id);
                  }
                }}
                style={{
                  cursor: "pointer",
                  padding: "8px 10px",
                  borderRadius: 8,
                  background: session.id === activeSessionId ? "#e6f4ff" : "transparent",
                  border: "none",
                }}
              >
                <Flex justify="space-between" align="center" style={{ width: "100%" }}>
                  {editingSessionId === session.id ? (
                    <Input
                      size="small"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onPressEnter={handleSaveRename}
                      onKeyDown={(e) => {
                        if (e.key === "Escape") {
                          setEditingSessionId(null);
                        }
                      }}
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                      suffix={
                        <Flex gap={4}>
                          <CheckOutlined
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSaveRename();
                            }}
                            style={{ color: "#52c41a", cursor: "pointer" }}
                          />
                          <CloseOutlined
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingSessionId(null);
                            }}
                            style={{ color: "#ff4d4f", cursor: "pointer" }}
                          />
                        </Flex>
                      }
                      style={{ width: "100%" }}
                    />
                  ) : (
                    <>
                      <Text ellipsis style={{ maxWidth: 160 }}>
                        {session.title || "New conversation"}
                      </Text>
                      <Dropdown
                        menu={{
                          items: menuItems,
                          onClick: ({ key, domEvent }) => {
                            domEvent.stopPropagation();
                            handleMenuClick(key, session);
                          },
                        }}
                        trigger={["click"]}
                        placement="bottomRight"
                      >
                        <Button
                          type="text"
                          size="small"
                          icon={<MoreOutlined style={{ fontSize: 16 }} />}
                          onClick={(e) => e.stopPropagation()}
                          style={{ opacity: 0.6 }}
                        />
                      </Dropdown>
                    </>
                  )}
                </Flex>
              </List.Item>
            )}
          />
        )}
      </div>
    </Flex>
  );
}