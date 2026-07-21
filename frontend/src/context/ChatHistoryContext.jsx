import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  listSessions,
  deleteSession as deleteSessionApi,
  renameSession as renameSessionApi,
} from "../apis/chatSessionApi";
import { useAuth } from "./AuthContext";

const ChatHistoryContext = createContext(null);

/**
 * Holds the current user's chat session list so it can be shared between
 * the always-visible history sidebar (in AppLayout) and ChatPage, which
 * needs to trigger a refresh whenever a new session is created or a
 * session's title/recency changes.
 */
export function ChatHistoryProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  const refreshSessions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSessions();
      setSessions(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      refreshSessions();
    } else {
      setSessions([]);
      setLoading(false);
    }
  }, [isAuthenticated, refreshSessions]);

  const removeSession = useCallback(async (sessionId) => {
    await deleteSessionApi(sessionId);
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
  }, []);

  const renameSession = useCallback(async (sessionId, newTitle) => {
    const updated = await renameSessionApi(sessionId, newTitle);
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, title: updated.title } : s))
    );
    return updated;
  }, []);

  const value = { sessions, loading, refreshSessions, removeSession, renameSession };

  return <ChatHistoryContext.Provider value={value}>{children}</ChatHistoryContext.Provider>;
}

export function useChatHistory() {
  const ctx = useContext(ChatHistoryContext);
  if (!ctx) throw new Error("useChatHistory must be used within a ChatHistoryProvider");
  return ctx;
}