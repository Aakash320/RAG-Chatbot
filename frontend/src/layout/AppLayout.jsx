import React from "react";
import { Layout, Menu, Typography, Flex } from "antd";
import { MessageOutlined, FileTextOutlined, RobotOutlined, RobotFilled } from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import { ROUTES } from "../constants/routes";

const { Sider, Content, Header } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: ROUTES.CHAT, icon: <MessageOutlined />, label: "Chat" },
  { key: ROUTES.DOCUMENTS, icon: <FileTextOutlined />, label: "Documents" },
];

export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey =
    menuItems.find((item) => location.pathname.startsWith(item.key))?.key ??
    ROUTES.CHAT;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider breakpoint="lg" collapsedWidth={0} theme="light" width={220}>
        <div
          style={{
            height: 56,
            display: "flex",
            alignItems: "center",
            paddingInline: 20,
          }}
        >
        <RobotFilled style={{ fontSize: 18, background: "#cae5fdff", borderRadius: "20px", padding: "10px" , marginLeft: 0, marginTop: 0, }} />
            {/* <Title level={5} style={{ margin: 0, padding:0 }}>
              RAG Chatbot
            </Title> */}
        </div>
        <Menu
          mode="inline"
          theme="light"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            borderLeft: "1px solid #f2f2f2ff",
            // border: "none",
            display: "flex",
            alignItems: "center",
            paddingInline: 24,
            marginLeft: 5,
          }}
        >
          {/* <Typography.Text strong>
            {menuItems.find((item) => item.key === selectedKey)?.label}
          </Typography.Text> */}
          <Title level={5} style={{ marginTop: 5 }}>
            RAG Chatbot
          </Title>
        </Header>
        <Content style={{ paddingLeft: 5, paddingBottom:0, overflow: "auto" }}>{children}</Content>
      </Layout>
    </Layout>
  );
}
