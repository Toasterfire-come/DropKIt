import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: `${BASE}/api`,
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // send httpOnly cookies
});

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
