import React, {useState} from "react";
import { Layout, Menu, Typography, Button, Tooltip} from "antd";
import { MessageOutlined, FileTextOutlined, RobotFilled, MenuFoldOutlined, MenuUnfoldOutlined } from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import { ROUTES, NAV_ITEMS } from "../constants/routes";

const { Sider, Content, Header } = Layout;
const { Title } = Typography;

const ICONS_BY_ROUTE = {
  [ROUTES.CHAT]: <MessageOutlined />,
  [ROUTES.DOCUMENTS]: <FileTextOutlined />,
};

const menuItems = NAV_ITEMS.map((item) => ({ ...item, icon: ICONS_BY_ROUTE[item.key] }));

export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();

  const [collapsed, setCollapsed] = useState(false);

  const selectedKey =
    menuItems.find((item) => location.pathname.startsWith(item.key))?.key ??
    ROUTES.CHAT;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        breakpoint="lg"
        collapsedWidth={0}
        theme="light"
        width={220}
        collapsible
        collapsed={collapsed}
        trigger={null}
      >
        <div
          onClick={() => setCollapsed(!collapsed)}
          style={{
            height: 56,
            display: "flex",
            alignItems: "center",
            paddingInline: 20,
            cursor: "pointer",
          }}
        >
          <RobotFilled style={{ fontSize: 18, background: "#cae5fdff", borderRadius: "20px", padding: "10px", marginLeft: 0, marginTop: 0 }} />
        </div>
        <Menu
          mode="inline"
          theme="light"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
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
            // border: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
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
              style={{border: "1px solid lightgray"}}
            >
              Docs
            </Button>
          </Tooltip>

        </Header>
        <Content style={{ paddingLeft: 5, paddingBottom:0, overflow: "auto" }}>{children}</Content>
      </Layout>
    </Layout>
  );
}
