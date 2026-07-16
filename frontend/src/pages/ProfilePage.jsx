import React from "react";
import { Card, Typography, Descriptions, Avatar, Flex, Button, Tag } from "antd";
import { UserOutlined, LogoutOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ROUTES } from "../constants/routes";

const { Title, Text } = Typography;

function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return "—";
  }
}

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  return (
    <Card style={{
    width: "100%",
    height: "100%",
    borderRadius: 0,
    border: "none",
  }}>
      <Flex align="center" gap={16} style={{ marginBottom: 24 }}>
        <Avatar size={64} icon={<UserOutlined />} style={{ background: "#a6c7f5ff" }} />
        <div>
          <Flex align="center" gap={8}>
            <Title level={4} style={{ margin: 0 }}>
              {user?.full_name || user?.email}
            </Title>
            <Tag color={user?.is_active ? "green" : "red"}>
              {user?.is_active ? "Active" : "Inactive"}
            </Tag>
          </Flex>
          <Text type="secondary">{user?.email}</Text>
        </div>
      </Flex>

      <Descriptions column={1} bordered size="middle">
        <Descriptions.Item label="Email">{user?.email}</Descriptions.Item>
        <Descriptions.Item label="Full name">{user?.full_name || "—"}</Descriptions.Item>
        <Descriptions.Item label="Role">{user?.role}</Descriptions.Item>
        <Descriptions.Item label="Member since">{formatDate(user?.created_at)}</Descriptions.Item>
      </Descriptions>

      <Flex style={{ marginTop: 24 }}>
        <Button danger icon={<LogoutOutlined />} onClick={handleLogout}>
          Log out
        </Button>
      </Flex>
    </Card>
  );
}