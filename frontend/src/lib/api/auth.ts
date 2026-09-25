/**
 * Auth endpoints defined by docs/03-api-contract-v0.1.md.
 * Session state is owned by the backend and transported only via HttpOnly cookie.
 */
import { api } from "./client";
import type { AuthContext, ChangePasswordResult, LogoutResult } from "@/types/auth";

export const authApi = {
  login: (username: string, password: string) => api.post<AuthContext>("/auth/login", { username, password }),
  me: () => api.get<AuthContext>("/auth/me"),
  changePassword: (newPassword: string) => api.post<ChangePasswordResult>("/auth/change-password", { new_password: newPassword }),
  logout: () => api.post<LogoutResult>("/auth/logout"),
};
