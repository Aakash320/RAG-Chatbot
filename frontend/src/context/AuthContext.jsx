import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import * as authApi from "../apis/authApi";
import { attachRefreshHandler, setAccessToken } from "../apis/httpClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  const doRefresh = useCallback(async () => {
    try {
      const data = await authApi.refresh();
      setUser(data.user);
      return data.access_token;
    } catch {
      setUser(null);
      setAccessToken(null);
      return null;
    }
  }, []);

  useEffect(() => {
    attachRefreshHandler(doRefresh);
  }, [doRefresh]);

  // On first load, try a silent refresh using the HttpOnly cookie — this
  // is what keeps someone logged in across a page reload without ever
  // storing the access token anywhere persistent.
  useEffect(() => {
    (async () => {
      await doRefresh();
      setIsBootstrapping(false);
    })();
  }, [doRefresh]);

  const login = async (email, password) => {
    const data = await authApi.login(email, password);
    setUser(data.user);
    return data.user;
  };

  const register = async (payload) => authApi.register(payload);

  const logout = async () => {
    await authApi.logout();
    setUser(null);
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isBootstrapping,
    login,
    logout,
    register,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}