import axios from "axios";

// ============================================================
// DIAGNOSTIC LOGGING — remove after confirming the fix
// ============================================================
const _REACT_APP_BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const _NODE_ENV = process.env.NODE_ENV;
const _BASE = _REACT_APP_BACKEND_URL || "";
const _origin = window.location.origin;

console.group("%c[api.js] DIAGNOSTIC", "color:cyan;font-weight:bold");
console.log("window.location.origin    =", _origin);
console.log("process.env.NODE_ENV      =", _NODE_ENV);
console.log("process.env.REACT_APP_BACKEND_URL =", _REACT_APP_BACKEND_URL);
console.log("Resolved BASE             =", JSON.stringify(_BASE));
console.log("Resolved baseURL (FINAL)  =", `${_BASE}/api`);
console.groupEnd();
// ============================================================

export const api = axios.create({
  baseURL: `${_BASE}/api`,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// --- Axios request interceptor — log every request URL ---
api.interceptors.request.use(
  (config) => {
    console.log(
      `%c[api.js REQ] %c${config.method?.toUpperCase()} %c${config.baseURL}${config.url}`,
      "color:gray",
      "color:yellow;font-weight:bold",
      "color:cyan"
    );
    return config;
  },
  (error) => {
    console.error("[api.js REQ ERROR]", error);
    return Promise.reject(error);
  }
);

// --- Axios response interceptor — log every response / error ---
api.interceptors.response.use(
  (response) => {
    console.log(
      `%c[api.js RES] %c${response.status} %c${response.config.baseURL}${response.config.url}`,
      "color:gray",
      "color:green;font-weight:bold",
      "color:cyan"
    );
    return response;
  },
  (error) => {
    console.error(
      `%c[api.js ERR] %c${error.message}`,
      "color:red;font-weight:bold",
      "color:orange"
    );
    if (error.config) {
      console.error("  Request URL:", `${error.config.baseURL}${error.config.url}`);
      console.error("  Method:", error.config.method);
      console.error("  withCredentials:", error.config.withCredentials);
    }
    if (error.response) {
      console.error("  Response status:", error.response.status);
      console.error("  Response headers:", error.response.headers);
    } else if (error.request) {
      console.error("  No response received — request was sent but never got a response");
      console.error("  XMLHttpRequest status:", error.request.status);
      console.error("  XMLHttpRequest readyState:", error.request.readyState);
    } else {
      console.error("  Request setup failed before sending");
    }
    return Promise.reject(error);
  }
);

export function formatApiError(err) {
  const d = err?.response?.data?.detail;
  if (d == null) return err?.message || "Something went wrong.";
  if (typeof d === "string") return d;
  if (Array.isArray(d))
    return d
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (d && typeof d.msg === "string") return d.msg;
  return String(d);
}

export default api;
