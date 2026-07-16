import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import { AuthProvider } from "./context/AuthContext";
import { ChatHistoryProvider } from "./context/ChatHistoryContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import AppLayout from "./layout/AppLayout";
import ChatPage from "./pages/ChatPage";
import DocumentPage from "./pages/DocumentPage";
import ProfilePage from "./pages/ProfilePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
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
        <AuthProvider>
          <ChatHistoryProvider>
            <Routes>
              <Route path={ROUTES.LOGIN} element={<LoginPage />} />
              <Route path={ROUTES.REGISTER} element={<RegisterPage />} />

              <Route element={<ProtectedRoute />}>
                <Route path="/" element={<Navigate to={ROUTES.CHAT} replace />} />
                <Route
                  path={ROUTES.CHAT}
                  element={
                    <AppLayout>
                      <ChatPage />
                    </AppLayout>
                  }
                />
                <Route
                  path={`${ROUTES.CHAT}/:sessionId`}
                  element={
                    <AppLayout>
                      <ChatPage />
                    </AppLayout>
                  }
                />
                <Route
                  path={ROUTES.DOCUMENTS}
                  element={
                    <AppLayout>
                      <DocumentPage />
                    </AppLayout>
                  }
                />
                <Route
                  path={ROUTES.PROFILE}
                  element={
                    <AppLayout>
                      <ProfilePage />
                    </AppLayout>
                  }
                />
                <Route path="*" element={<Navigate to={ROUTES.CHAT} replace />} />
              </Route>
            </Routes>
          </ChatHistoryProvider>
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  );
}