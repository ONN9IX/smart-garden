/**
 * Shared HTTP client for the Stage 1 API.
 * Source of truth: docs/03-api-contract-v0.1.md.
 * Security: browser sends the HttpOnly cookie; JavaScript never reads its value.
 */
const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

type ApiErrorCode =
  | "INVALID_CREDENTIALS"
  | "USER_BLOCKED"
  | "ORGANIZATION_BLOCKED"
  | "PASSWORD_CHANGE_REQUIRED"
  | "INVALID_PASSWORD"
  | "USERNAME_ALREADY_EXISTS"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "VALIDATION_ERROR"
  | "INTERNAL_ERROR";

const errorMessages: Partial<Record<ApiErrorCode, string>> = {
  INVALID_CREDENTIALS: "Неверный логин или пароль",
  USER_BLOCKED: "Доступ к аккаунту заблокирован. Обратитесь к администратору сада.",
  ORGANIZATION_BLOCKED: "Доступ к детскому саду заблокирован. Обратитесь к администратору.",
  PASSWORD_CHANGE_REQUIRED: "Сначала измените временный пароль.",
  INVALID_PASSWORD: "Пароль не соответствует требованиям. Выберите другой пароль.",
  UNAUTHORIZED: "Сессия завершилась. Войдите снова.",
  FORBIDDEN: "Действие недоступно для вашей учётной записи.",
  VALIDATION_ERROR: "Проверьте введённые данные.",
  INTERNAL_ERROR: "Не удалось выполнить запрос. Попробуйте ещё раз.",
};

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    public readonly status: number,
    message: string,
    public readonly field: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class NetworkError extends Error {
  constructor() {
    super("Нет соединения с сервером. Проверьте подключение и попробуйте ещё раз.");
    this.name = "NetworkError";
  }
}

export function userMessage(error: unknown, fallback = "Не удалось выполнить запрос. Попробуйте ещё раз."): string {
  if (error instanceof NetworkError || error instanceof ApiError) return error.message;
  return fallback;
}

async function request<T>(path: string, options: { method?: "GET" | "POST"; body?: object } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method: options.method ?? "GET",
      headers: options.body ? { "Content-Type": "application/json" } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
      credentials: "include",
      cache: "no-store",
    });
  } catch {
    throw new NetworkError();
  }

  if (!response.ok) {
    // Only the documented code/field are accepted. Never surface raw server text.
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    const error = typeof payload === "object" && payload !== null && "error" in payload
      ? (payload as { error: unknown }).error
      : null;
    const detail = typeof error === "object" && error !== null ? error as Record<string, unknown> : {};
    const code = typeof detail.code === "string" ? detail.code : "UNKNOWN";
    const field = typeof detail.field === "string" ? detail.field : null;
    throw new ApiError(code, response.status, errorMessages[code as ApiErrorCode] ?? "Не удалось выполнить запрос. Попробуйте ещё раз.", field);
  }

  try {
    return await response.json() as T;
  } catch {
    throw new ApiError("INVALID_RESPONSE", response.status, "Сервер вернул некорректный ответ. Попробуйте ещё раз.");
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: object) => request<T>(path, { method: "POST", body }),
};
