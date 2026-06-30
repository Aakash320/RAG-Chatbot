import React, { useState } from "react";
import { Card, Flex } from "antd";
import ChatWindow from "../components/chat/ChatWindow";
import ChatSender from "../components/chat/ChatSender";
import { Typography } from "antd";
import { sendChatMessage } from "../apis/chatApi";
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
      // TODO: sendChatMessage() in apis/chatApi.js is currently a placeholder for POST /chat.
      const reply = await sendChatMessage(text);
      // const reply = {
      //   id: `placeholder-${Date.now()}`,
      //   role: "assistant",
      //   content: "This is a placeholder AI response. Connect the real chat API to replace this.",
      //   createdAt: new Date().toISOString(),
      // }

      setMessages((prev) =>
        prev.map((message) =>
          message.key === loadingMessage.key
            ? { key: reply.id ?? nextKey(), role: "assistant", content: reply.content }
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
                content: "Something went wrong getting a response. Please try again.",
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
      style={{ height: "calc(100vh - 70px)", borderRadius: 0, border: "none" }}
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
