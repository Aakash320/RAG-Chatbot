import React, { useState } from "react";
import { Button, Card, Flex, Form, Input, Typography, Alert } from "antd";
import { RobotFilled } from "@ant-design/icons";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../apis/httpClient";
import { ROUTES } from "../constants/routes";

const { Title, Text } = Typography;

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleFinish = async ({ email, password }) => {
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      const redirectTo = location.state?.from?.pathname || ROUTES.CHAT;
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, "Could not sign in. Check your email and password."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Flex align="center" justify="center" style={{ height: "100vh", background: "#fafafa" }}>
      <Card style={{ width: 380 }}>
        <Flex vertical align="center" gap={4} style={{ marginBottom: 24 }}>
          <RobotFilled style={{ fontSize: 20, background: "#cae5fdff", borderRadius: 20, padding: 10 }} />
          <Title level={4} style={{ margin: "12px 0 0" }}>Sign in</Title>
          <Text type="secondary">Welcome back to RAG Chatbot</Text>
        </Flex>

        {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

        <Form layout="vertical" onFinish={handleFinish} disabled={submitting}>
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: "Enter your email" },
              { type: "email", message: "Enter a valid email" },
            ]}
          >
            <Input autoFocus placeholder="you@example.com" />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true, message: "Enter your password" }]}>
            <Input.Password placeholder="••••••••" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block loading={submitting}>
              Sign in
            </Button>
          </Form.Item>
        </Form>

        <Text type="secondary">
          Don't have an account? <Link to={ROUTES.REGISTER}>Create one</Link>
        </Text>
      </Card>
    </Flex>
  );
}