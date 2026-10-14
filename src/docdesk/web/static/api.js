// Calls to the DocDesk API. The token lives in sessionStorage for this tab only.

const KEY = "docdesk_token";

export function getToken() {
  try {
    return sessionStorage.getItem(KEY);
  } catch (error) {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) sessionStorage.setItem(KEY, token);
    else sessionStorage.removeItem(KEY);
  } catch (error) {
    // Storage can be blocked. The page still works until it is reloaded.
  }
}

// Returns {status, data, error}. A network failure gives status 0, never an exception.
async function post(path, body, withToken) {
  const headers = { "content-type": "application/json" };
  const token = getToken();
  if (withToken && token) headers.authorization = "Bearer " + token;
  try {
    const response = await fetch(path, { method: "POST", headers, body: JSON.stringify(body) });
    const json = await response.json().catch(() => ({}));
    return { status: response.status, data: json.data || null, error: json.error || null };
  } catch (error) {
    return { status: 0, data: null, error: { code: "network", message: "Cannot reach the server" } };
  }
}

export async function login(email, password) {
  const result = await post("/auth/login", { email, password }, false);
  if (result.data) setToken(result.data.access_token);
  return result;
}

export function register(email, password) {
  return post("/auth/register", { email, password }, false);
}

export function retrieve(question) {
  return post("/retrieve", { question }, true);
}

export function query(question) {
  return post("/query", { question }, true);
}

export function logout() {
  setToken(null);
}
