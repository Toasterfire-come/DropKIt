import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "./api";

// ----- Auth context -------------------------------------------------------
const AuthCtx = createContext({ user: null, loading: true });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const r = await api.get("/auth/me", { validateStatus: (s) => s < 500 });
      if (r.status === 200) setUser(r.data);
      else setUser(null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    setUser(r.data);
    return r.data;
  };

  const register = async (email, password, name) => {
    const r = await api.post("/auth/register", { email, password, name });
    setUser(r.data);
    return r.data;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {}
    setUser(null);
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout, refresh, formatApiError }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);

// ----- UI mode context ----------------------------------------------------
const UIModeCtx = createContext({ mode: "waitlist", loading: true });

export function UIModeProvider({ children }) {
  const [mode, setMode] = useState("waitlist");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/ui-mode");
      setMode(r.data.mode);
    } catch {
      setMode("waitlist");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const setRemoteMode = async (next) => {
    const r = await api.post("/ui-mode", { mode: next });
    setMode(r.data.mode);
    return r.data.mode;
  };

  return (
    <UIModeCtx.Provider value={{ mode, loading, setRemoteMode, refresh: load }}>
      {children}
    </UIModeCtx.Provider>
  );
}

export const useUIMode = () => useContext(UIModeCtx);
