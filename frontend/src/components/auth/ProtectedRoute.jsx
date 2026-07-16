import React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Flex, Spin } from "antd";
import { useAuth } from "../../context/AuthContext";
import { ROUTES } from "../../constants/routes";

export default function ProtectedRoute() {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();

  if (isBootstrapping) {
    return (
      <Flex align="center" justify="center" style={{ height: "100vh" }}>
        <Spin size="large" />
      </Flex>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace state={{ from: location }} />;
  }

  return <Outlet />;
}