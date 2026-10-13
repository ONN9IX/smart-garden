/** Independent platform API. CSRF is held in memory; cookies remain HttpOnly. */
import type {
  CreateOrganization,
  PlatformAudit,
  PlatformIdentity,
  PlatformOrganization,
  PlatformOverview,
  Provisioning,
  Subscription,
} from "@/types/platform";
const base = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");
let csrf = "";
export class PlatformError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
async function request<T>(
  path: string,
  method = "GET",
  body?: object,
  login = false,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${base}/platform${path}`, {
      method,
      credentials: "include",
      cache: "no-store",
      headers: body
        ? {
            "Content-Type": "application/json",
            "X-Platform-CSRF": login ? "login" : csrf,
          }
        : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new PlatformError(0, "Нет соединения. Повторите запрос.");
  }
  const result = await response.json();
  if (!response.ok)
    throw new PlatformError(
      response.status,
      response.status === 503
        ? "Защищённый кабинет или передача учётных данных не настроены."
        : response.status === 429
          ? "Слишком много попыток. Повторите позже."
          : result.error?.message || "Запрос недоступен.",
    );
  return result as T;
}
async function identity(path: string, body?: object) {
  const result = await request<PlatformIdentity>(
    path,
    body ? "POST" : "GET",
    body,
  );
  csrf = result.csrf_token;
  return result;
}
export const platformApi = {
  login: async (username: string, password: string) => {
    const result = await request<{ csrf_token: string }>(
      "/auth/login",
      "POST",
      { username, password },
      true,
    );
    csrf = result.csrf_token;
  },
  verify: (code: string) => identity("/auth/mfa/verify", { code }),
  stepUp: (code: string) => identity("/auth/step-up", { code }),
  me: () => identity("/auth/me"),
  logout: async () => {
    await request("/auth/logout", "POST", {});
    csrf = "";
  },
  clear: () => {
    csrf = "";
  },
  overview: () => request<PlatformOverview>("/overview"),
  organizations: (search = "", status = "") =>
    request<PlatformOrganization[]>(
      `/organizations?search=${encodeURIComponent(search)}${status ? `&status=${encodeURIComponent(status)}` : ""}`,
    ),
  organization: (id: string) =>
    request<PlatformOrganization>(`/organizations/${encodeURIComponent(id)}`),
  provision: (data: CreateOrganization) =>
    request<Provisioning>("/organizations", "POST", data),
  lifecycle: (
    id: string,
    block: boolean,
    confirmation_name: string,
    reason: string,
  ) =>
    request<PlatformOrganization>(
      `/organizations/${encodeURIComponent(id)}/${block ? "block" : "unblock"}`,
      "POST",
      { confirmation_name, reason },
    ),
  subscription: (
    id: string,
    confirmation_name: string,
    subscription: Subscription,
  ) =>
    request<Subscription>(
      `/organizations/${encodeURIComponent(id)}/subscription`,
      "PATCH",
      { confirmation_name, subscription },
    ),
  changeProfile: (id: string, confirmation_name: string, operating_profile: PlatformOrganization["operating_profile"]) =>
    request<PlatformOrganization>(`/organizations/${encodeURIComponent(id)}/profile`, "PATCH", { confirmation_name, operating_profile }),
  audit: (id?: string) =>
    request<PlatformAudit[]>(
      `/audit${id ? `?organization_id=${encodeURIComponent(id)}` : ""}`,
    ),
};
