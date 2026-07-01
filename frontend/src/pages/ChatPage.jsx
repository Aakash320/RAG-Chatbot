import React, { useState } from "react";
import { Card, Flex } from "antd";
import ChatWindow from "../components/chat/ChatWindow";
import ChatSender from "../components/chat/ChatSender";
import { Typography } from "antd";
import { sendChatMessage } from "../apis/chatApi";
import { getErrorMessage } from "../apis/httpClient";
import { RobotOutlined, RobotFilled } from "@ant-design/icons";

const {Title} = Typography

let messageCounter = 0;
const nextKey = () => `msg-${Date.now()}-${messageCounter++}`;

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);

  const handleSend = async (text) => {
    const userMessage = { key: nextKey(), role: "user", content: text };
    const loadingMessage = {
      key: nextKey(),
      role: "assistant",
      content: "Thinking...",
      loading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setIsSending(true);

    try {
      const { answer, sources } = await sendChatMessage(text);

      setMessages((prev) =>
        prev.map((message) =>
          message.key === loadingMessage.key
            ? { key: nextKey(), role: "assistant", content: answer, sources }
            : message
        )
      );
    } catch (error) {
      setMessages((prev) =>
        prev.map((message) =>
          message.key === loadingMessage.key
            ? {
                ...message,
                loading: false,
                content: getErrorMessage(
                  error,
                  "Something went wrong getting a response. Please try again."
                ),
              }
            : message
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Card
      style={{ height: "calc(100vh - 70px)", borderRadius: 0, }}
      // style={{ height: "100vh" }}
      styles={{
        body: {
          height: "100%",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          padding: 16,
        },
      }}
    >
      <div style={{ flex: 1, overflow: "auto" }}>
        <ChatWindow messages={messages} onPromptSelect={handleSend} />
      </div>
      <Flex justify="center" style={{ width: "100%" }}>
        <div style={{ width: "60%", minWidth: 560, maxWidth: 800 }}>
          <ChatSender onSend={handleSend} loading={isSending} />
        </div>
      </Flex>
    </Card>
  );
}
