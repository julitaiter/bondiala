const BASE = "/api/v1/";

function message(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(message).join(" ");
  if (value && typeof value === "object")
    return Object.entries(value)
      .map(
        ([key, entry]) =>
          `${["error", "detail", "non_field_errors"].includes(key) ? "" : `${key}: `}${message(entry)}`,
      )
      .join(" ");
  return "No se pudo completar la operación.";
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (options.method && !["GET", "HEAD", "OPTIONS"].includes(options.method)) {
    const csrfResponse = await fetch(`${BASE}auth/csrf/`, {
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!csrfResponse.ok)
      throw new Error(
        "No pudimos iniciar la sesión de seguridad. Intentá otra vez.",
      );
    const csrf = await csrfResponse.json();
    headers.set("X-CSRFToken", csrf.csrfToken);
  }
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({
        error:
          response.status === 429
            ? "Demasiados intentos. Esperá un momento y volvé a probar."
            : "No pudimos cargar la información. Intentá de nuevo.",
      }));
    throw new Error(message(body));
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const mutate = <T>(path: string, body: unknown, method = "POST") =>
  api<T>(path, { method, body: JSON.stringify(body) });
