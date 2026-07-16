import React, { useEffect, useRef, useState } from "react";
import { Alert, Card, Flex } from "antd";
import { useNavigate, useParams } from "react-router-dom";
import ChatWindow from "../components/chat/ChatWindow";
import ChatSender from "../components/chat/ChatSender";
import { streamChatMessage } from "../apis/chatApi";
import { getSessionMessages } from "../apis/chatSessionApi";
import { getErrorMessage } from "../apis/httpClient";
import { ROUTES } from "../constants/routes";
import { useChatHistory } from "../context/ChatHistoryContext";

let messageCounter = 0;
const nextKey = () => `msg-${Date.now()}-${messageCounter++}`;

/** Maps a backend ChatMessageOut record into the local bubble shape. */
function fromServerMessage(m) {
  return {
    key: m.id,
    role: m.role,
    content: m.content,
    loading: false,
    done: true,
    statusSteps: m.thought_steps || [],
    sources: m.sources || undefined,
  };
}

export default function ChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { refreshSessions } = useChatHistory();
  // Set right before we self-navigate to a newly-created session's URL, so
  // the load-on-sessionId-change effect below doesn't clobber the
  // in-progress streamed messages with a server refetch.
  const skipNextLoadRef = useRef(null);

  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    if (sessionId && skipNextLoadRef.current === sessionId) {
      skipNextLoadRef.current = null;
      return;
    }
    if (!sessionId) {
      setMessages([]);
      return;
    }
    setIsLoadingSession(true);
    setLoadError(null);
    getSessionMessages(sessionId)
      .then((serverMessages) => setMessages(serverMessages.map(fromServerMessage)))
      .catch((err) => setLoadError(getErrorMessage(err, "Could not load this conversation.")))
      .finally(() => setIsLoadingSession(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

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

    const isNewSession = !sessionId;

    try {
      await streamChatMessage(text, sessionId || null, null, null, {
        onSession: ({ session_id }) => {
          if (isNewSession) {
            skipNextLoadRef.current = session_id;
            navigate(`${ROUTES.CHAT}/${session_id}`, { replace: true });
          }
        },
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
          refreshSessions();
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
    <Flex style={{ height: "calc(100vh - 70px)" }}>
      <Card
        style={{ flex: 1, borderRadius: 0, borderLeft: "none" }}
        styles={{
          body: {
            height: "100%",
            display: "flex",
            flexDirection: "column",
            gap: 16,
            padding: 16,
          },
        }}
        loading={isLoadingSession}
      >
        {loadError ? (
          <Alert type="error" message={loadError} showIcon />
        ) : (
          <div style={{ flex: 1, overflow: "auto" }}>
            <ChatWindow messages={messages} onPromptSelect={handleSend} />
          </div>
        )}
        <Flex justify="center" style={{ width: "100%" }}>
          <div style={{ width: "60%", minWidth: 560, maxWidth: 800 }}>
            <ChatSender onSend={handleSend} loading={isSending} />
          </div>
        </Flex>
      </Card>
    </Flex>
  );
}