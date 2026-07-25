import { cookies, headers as requestHeaders } from "next/headers";

import { forwardClientAddress } from "@/lib/proxy-headers";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

function internalApiUrl() {
  return process.env.INTERNAL_API_URL ?? "http://localhost:8000";
}

export function publicApiUrl() {
  return process.env.PUBLIC_API_URL ?? "http://localhost:8000";
}

export async function serverApi<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const cookieStore = await cookies();
  const incomingHeaders = await requestHeaders();
  const cookieHeader = cookieStore
    .getAll()
    .map(({ name, value }) => `${name}=${value}`)
    .join("; ");
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  forwardClientAddress(headers, incomingHeaders);
  if (cookieHeader) {
    headers.set("Cookie", cookieHeader);
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = cookieStore.get("rayo_csrf")?.value;
  if (csrf && init.method && !["GET", "HEAD"].includes(init.method.toUpperCase())) {
    headers.set("X-CSRF-Token", csrf);
  }

  const response = await fetch(`${internalApiUrl()}/api/v1${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    let message = "Não foi possível concluir esta ação.";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep the safe generic message for non-JSON upstream errors.
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
