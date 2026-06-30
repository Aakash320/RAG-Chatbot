import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import AppLayout from "./layout/AppLayout";
import ChatPage from "./pages/ChatPage";
import DocumentPage from "./pages/DocumentPage";
import { ROUTES } from "./constants/routes";

export default function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#1677ff",
          borderRadius: 8,
        },
      }}
    >
      <BrowserRouter>
        <AppLayout>
          <Routes>
            <Route path="/" element={<Navigate to={ROUTES.CHAT} replace />} />
            <Route path={ROUTES.CHAT} element={<ChatPage />} />
            <Route path={ROUTES.DOCUMENTS} element={<DocumentPage />} />
            <Route path="*" element={<Navigate to={ROUTES.CHAT} replace />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </ConfigProvider>
  );
}
