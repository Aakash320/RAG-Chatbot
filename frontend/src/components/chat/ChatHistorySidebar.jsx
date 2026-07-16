import React from "react";
import { Button, Empty, Flex, List, Popconfirm, Spin, Tooltip, Typography } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import { useChatHistory } from "../../context/ChatHistoryContext";
import { ROUTES } from "../../constants/routes";

const { Text } = Typography;

/**
 * Chat history panel rendered inside the app's persistent sidebar.
 * Reads/writes the session list via ChatHistoryContext, and drives
 * navigation directly so it works from any page (chat, documents, profile).
 */
export default function ChatHistorySidebar() {
  const navigate = useNavigate();
  const { sessionId: activeSessionId } = useParams();
  const { sessions, loading, removeSession } = useChatHistory();

  const handleNewChat = () => navigate(ROUTES.CHAT);
  const handleSelect = (sessionId) => navigate(`${ROUTES.CHAT}/${sessionId}`);

  const handleDelete = async (sessionId) => {
    await removeSession(sessionId);
    if (sessionId === activeSessionId) handleNewChat();
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
                onClick={() => handleSelect(session.id)}
                style={{
                  cursor: "pointer",
                  padding: "8px 10px",
                  borderRadius: 8,
                  background: session.id === activeSessionId ? "#e6f4ff" : "transparent",
                  border: "none",
                }}
              >
                <Flex justify="space-between" align="center" style={{ width: "100%" }}>
                  <Text ellipsis style={{ maxWidth: 140 }}>
                    {session.title || "New conversation"}
                  </Text>
                  <Popconfirm
                    title="Delete this conversation?"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      handleDelete(session.id);
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                  >
                    <Tooltip title="Delete">
                      <DeleteOutlined onClick={(e) => e.stopPropagation()} style={{ opacity: 0.5 }} />
                    </Tooltip>
                  </Popconfirm>
                </Flex>
              </List.Item>
            )}
          />
        )}
      </div>
    </Flex>
  );
}