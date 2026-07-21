import React, { useState } from "react";
import { Layout, Typography, Button, Tooltip, Flex, Dropdown, Avatar } from "antd";
import {
  FileTextOutlined,
  RobotFilled,
  UserOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import { ROUTES } from "../constants/routes";
import { useAuth } from "../context/AuthContext";
import ChatHistorySidebar from "../components/chat/ChatHistorySidebar";

const { Sider, Content, Header } = Layout;
const { Title, Text } = Typography;

export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();

  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  const [collapsed, setCollapsed] = useState(false);

  const profileMenuItems = [
    { key: "email", label: user?.email, disabled: true },
    { key: "role", label: `Role: ${user?.role}`, disabled: true },
    { type: "divider" },
    { key: "profile", label: "Profile", onClick: () => navigate(ROUTES.PROFILE) },
    { type: "divider" },
    { key: "logout", label: "Log out", onClick: handleLogout },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        breakpoint="lg"
        collapsedWidth={0}
        theme="light"
        width={260}
        collapsible
        collapsed={collapsed}
        trigger={null}
      >
        {/*
          Sider wraps its children in its own internal div
          (.ant-layout-sider-children), so a flex style on <Sider> itself
          doesn't affect how *our* children stack. We create our own
          full-height flex column here instead so the profile block can
          stick to the bottom via marginTop: "auto".
        */}
        <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <div
            onClick={() => setCollapsed(!collapsed)}
            style={{
              height: 56,
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              paddingInline: 20,
              cursor: "pointer",
            }}
          >
            <RobotFilled style={{ fontSize: 18, background: "#cae5fdff", borderRadius: "20px", padding: "10px", marginLeft: 0, marginTop: 0 }} />
          </div>

          <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
            <ChatHistorySidebar />
          </div>

          <div style={{ flexShrink: 0, marginTop: "auto", borderTop: "1px solid #f0f0f0", padding: 12 }}>
            <Dropdown menu={{ items: profileMenuItems }} trigger={["click"]} placement="topRight">
              <Flex
                align="center"
                gap={10}
                style={{ cursor: "pointer", padding: 8, borderRadius: 8 }}
              >
                <Avatar style={{ background: "#a6c7f5ff", flexShrink: 0 }} icon={<UserOutlined />} />
                <div style={{ overflow: "hidden" }}>
                  <Text ellipsis style={{ display: "block", maxWidth: 150 }}>
                    {user?.full_name || user?.email}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {user?.role}
                  </Text>
                </div>
              </Flex>
            </Dropdown>
          </div>
        </div>
      </Sider>
      {collapsed && (
        <div
          onClick={() => setCollapsed(false)}
          style={{
            width: 50,
            background: "#fff",
            borderRight: "1px solid #f2f2f2ff",
            cursor: "pointer",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            paddingTop: 14,
          }}
        >
          <RobotFilled
            style={{
              fontSize: 18,
              background: "#cae5fdff",
              borderRadius: "20px",
              padding: "10px",
            }}
          />
        </div>
      )}
      <Layout>
        <Header
          style={{
            background: "#fff",
            borderLeft: "1px solid #f2f2f2ff",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            paddingInline: 24,
            marginLeft: 5,
          }}
        >
          <Title level={5} style={{ marginTop: 5 }}>
            RAG Chatbot
          </Title>

          <Flex align="center" gap={12}>
            {user?.role?.toLowerCase() === "admin" && (
              <Tooltip title="Documents">
                <Button
                  type={location.pathname.startsWith(ROUTES.DOCUMENTS) ? "default" : "text"}
                  shape="rectangle"
                  icon={<FileTextOutlined style={{ fontSize: 18 }} />}
                  onClick={() =>
                    navigate(
                      location.pathname.startsWith(ROUTES.DOCUMENTS) ? ROUTES.CHAT : ROUTES.DOCUMENTS
                    )
                  }
                  style={{ border: "1px solid lightgray" }}
                >
                  Docs
                </Button>
              </Tooltip>
            )}
          </Flex>
        </Header>
        <Content style={{ paddingLeft: 5, paddingBottom: 0, overflow: "auto" }}>{children}</Content>
      </Layout>
    </Layout>
  );
}