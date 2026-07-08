import React, { useState } from "react";
import { Card, Flex } from "antd";
import ChatWindow from "../components/chat/ChatWindow";
import ChatSender from "../components/chat/ChatSender";
import { streamChatMessage } from "../apis/chatApi";

let messageCounter = 0;
const nextKey = () => `msg-${Date.now()}-${messageCounter++}`;

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);

  const updateAssistantMessage = (key, updater) => {
    setMessages((prev) => prev.map((m) => (m.key === key ? updater(m) : m)));
  };

  const handleSend = async (text) => {
    const userMessage = { key: nextKey(), role: "user", content: text };
    const assistantKey = nextKey();
    const assistantMessage = {
      key: assistantKey,
      role: "assistant",
      content: "",
      loading: true,
      done: false,
      statusSteps: [],
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsSending(true);

    const HISTORY_WINDOW = 6;
    const chatHistory = messages
      .filter((m) => !m.loading)
      .slice(-HISTORY_WINDOW)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      await streamChatMessage(text, chatHistory, null, null, {
        onStatus: (status) => {
          updateAssistantMessage(assistantKey, (m) => ({
            ...m,
            loading: false,
            statusSteps: [...(m.statusSteps || []), status],
          }));
        },
        onToken: (delta) => {
          updateAssistantMessage(assistantKey, (m) => ({
            ...m,
            loading: false,
            content: m.content + delta,
          }));
        },
        onDone: ({ answer, sources }) => {
          updateAssistantMessage(assistantKey, (m) => ({
            ...m,
            loading: false,
            done: true,
            content: answer,
            sources,
          }));
        },
        onError: (detail) => {
          updateAssistantMessage(assistantKey, (m) => ({
            ...m,
            loading: false,
            done: true,
            hasError: true,
            content: detail,
          }));
        },
      });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Card
      style={{ height: "calc(100vh - 70px)", borderRadius: 0 }}
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
