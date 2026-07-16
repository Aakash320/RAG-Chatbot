import axios from "axios";

// Base URL for the backend API.
export const BASE_URL = "/api/v1";

// In-memory access token store — never localStorage, keeps it out of
// reach of XSS, matching the HttpOnly-cookie choice for the refresh
// token. Both the axios instance below and the raw fetch() call in
// chatApi.js (SSE needs a real stream, which axios can't give us) read
// from this same store.
let accessToken = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

const httpClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  withCredentials: true, // send the refresh-token cookie on /auth/refresh & /auth/logout
});

httpClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// On a 401, try exactly one silent refresh (using the HttpOnly cookie),
// then retry the original request once. `attachRefreshHandler` is called
// once from AuthContext (which owns the actual refresh call) — this
// indirection avoids a circular import between this file and authApi.js.
let refreshPromise = null;

export function attachRefreshHandler(refreshFn) {
  httpClient.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config;
      const status = error.response?.status;

      if (!original || status !== 401 || original._retried || original.url?.includes("/auth/")) {
        return Promise.reject(error);
      }
      original._retried = true;

      try {
        if (!refreshPromise) {
          refreshPromise = refreshFn().finally(() => {
            refreshPromise = null;
          });
        }
        const newToken = await refreshPromise;
        if (!newToken) throw error;
        original.headers.Authorization = `Bearer ${newToken}`;
        return httpClient(original);
      } catch {
        return Promise.reject(error);
      }
    }
  );
}

/**
 * Extract the backend's error detail (from AppError's JSON body:
 * { detail: "..." }) so components can show the real reason instead
 * of a generic message.
 */
export function getErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  return error?.response?.data?.detail || fallback;
}

export default httpClient;