import React, { useState } from "react";
import { Button, Card, Checkbox, Flex, Form, Input, Typography, Alert } from "antd";
import { RobotFilled } from "@ant-design/icons";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../apis/httpClient";
import { ROUTES } from "../constants/routes";

const { Title, Text } = Typography;

export default function RegisterPage() {
  const { register, login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleFinish = async ({ email, password, fullName, isAdmin }) => {
    setError(null);
    setSubmitting(true);
    try {
      await register({ email, password, fullName, role: isAdmin ? "admin" : "user" });
      // Registration doesn't log you in server-side — sign in right after
      // for a smooth "one form, then you're in" flow.
      await login(email, password);
      navigate(ROUTES.CHAT, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, "Could not create your account."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Flex align="center" justify="center" style={{ height: "100vh", background: "#fafafa" }}>
      <Card style={{ width: 400 }}>
        <Flex vertical align="center" gap={4} style={{ marginBottom: 24 }}>
          <RobotFilled style={{ fontSize: 20, background: "#cae5fdff", borderRadius: 20, padding: 10 }} />
          <Title level={4} style={{ margin: "12px 0 0" }}>Create an account</Title>
          <Text type="secondary">Get started with RAG Chatbot</Text>
        </Flex>

        {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

        <Form layout="vertical" onFinish={handleFinish} disabled={submitting}>
          <Form.Item name="fullName" label="Full name">
            <Input autoFocus placeholder="Jane Doe" />
          </Form.Item>
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: "Enter your email" },
              { type: "email", message: "Enter a valid email" },
            ]}
          >
            <Input placeholder="you@example.com" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Password"
            rules={[
              { required: true, message: "Enter a password" },
              { min: 8, message: "At least 8 characters" },
            ]}
          >
            <Input.Password placeholder="At least 8 characters" />
          </Form.Item>
          <Form.Item name="isAdmin" valuePropName="checked" style={{ marginBottom: 8 }}>
            <Checkbox>Register as an admin (can upload/delete documents)</Checkbox>
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block loading={submitting}>
              Create account
            </Button>
          </Form.Item>
        </Form>

        <Text type="secondary">
          Already have an account? <Link to={ROUTES.LOGIN}>Sign in</Link>
        </Text>
      </Card>
    </Flex>
  );
}