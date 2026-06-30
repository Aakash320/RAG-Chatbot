import axios from "axios";

// Base URL for the backend API.
// TODO: point this at your real backend, e.g. via an env var:
// const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const BASE_URL = "/api";

const httpClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// TODO: add request/response interceptors here later if needed
// (e.g. attaching auth tokens, global error handling, refreshing sessions).
//
// httpClient.interceptors.request.use((config) => {
//   const token = getAuthToken();
//   if (token) config.headers.Authorization = `Bearer ${token}`;
//   return config;
// });

export default httpClient;
