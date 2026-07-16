import httpClient, { setAccessToken } from "./httpClient";

/**
 * Auth API
 * Backend routes: POST /auth/register, /auth/login, /auth/refresh, /auth/logout, GET /auth/me
 *
 * Login uses OAuth2's form-encoded fields (username/password) to match
 * the backend's OAuth2PasswordRequestForm — `username` is the user's email.
 */

export async function register({ email, password, fullName, role }) {
  const { data } = await httpClient.post("/auth/register", {
    email,
    password,
    full_name: fullName || null,
    role: role || null, // omit -> backend defaults to "user"
  });
  return data; // UserPublic
}

export async function login(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const { data } = await httpClient.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  setAccessToken(data.access_token);
  return data; // { access_token, token_type, user }
}

export async function refresh() {
  const { data } = await httpClient.post("/auth/refresh");
  setAccessToken(data.access_token);
  return data; // { access_token, token_type, user }
}

export async function logout() {
  try {
    await httpClient.post("/auth/logout");
  } finally {
    setAccessToken(null);
  }
}

export async function getCurrentUser() {
  const { data } = await httpClient.get("/auth/me");
  return data;
}