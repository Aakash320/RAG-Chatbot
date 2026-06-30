import React, { useState } from "react";
import { Sender } from "@ant-design/x";

/**
 * ChatSender wraps Ant Design X's Sender input.
 * Calls onSend(text) when the user submits a message.
 */
export default function ChatSender({ onSend, loading }) {
  const [value, setValue] = useState("");

  const handleSubmit = (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend?.(trimmed);
    setValue("");
  };

  return (
    <Sender
      value={value}
      onChange={setValue}
      onSubmit={handleSubmit}
      loading={loading}
      placeholder="Ask anything about your documents..."
    />
  );
}
