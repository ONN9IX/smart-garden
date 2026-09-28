import { api } from "./client";
import type { DashboardSummary } from "@/types/stage4";

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary"),
};
