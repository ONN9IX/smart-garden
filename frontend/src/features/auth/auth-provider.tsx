"use client";

/**
 * In-memory auth context. /auth/me refreshes it after reload and password change.
 * Security: no credentials, password, session token, or tenant selector are persisted in JS storage.
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/auth";
import type { AuthContext as CurrentUser } from "@/types/auth";

type AuthState = "loading" | "ready" | "error";

interface AuthValue {
  current: CurrentUser | null;
  state: AuthState;
  refresh: () => Promise<CurrentUser | null>;
  clear: () => void;
}

const Context = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [current, setCurrent] = useState<CurrentUser | null>(null);
  const [state, setState] = useState<AuthState>("loading");

  const refresh = useCallback(async () => {
    setState("loading");
    try {
      const result = await authApi.me();
      setCurrent(result);
      setState("ready");
      return result;
    } catch (error) {
      setCurrent(null);
      if (error instanceof ApiError && error.status === 401) {
        setState("ready");
        return null;
      }
      setState("error");
      throw error;
    }
  }, []);

  useEffect(() => {
    // The browser, rather than the frontend application, retains the session cookie.
    void authApi.me().then((result) => {
      setCurrent(result);
      setState("ready");
    }).catch((error: unknown) => {
      setCurrent(null);
      setState(error instanceof ApiError && error.status === 401 ? "ready" : "error");
    });
  }, []);

  const clear = useCallback(() => {
    setCurrent(null);
    setState("ready");
  }, []);

  return <Context.Provider value={{ current, state, refresh, clear }}>{children}</Context.Provider>;
}

export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
