import axios from "axios";

// Base URL for the backend API.
// TODO: point this at your real backend, e.g. via an env var:
// const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const BASE_URL = "/api/v1";

const httpClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

/**
 * Extract the backend's error detail (from AppError's JSON body:
 * { detail: "..." }) so components can show the real reason instead
 * of a generic message.
 */
export function getErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  return error?.response?.data?.detail || fallback;
}

export default httpClient;