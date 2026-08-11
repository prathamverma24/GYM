import type { ApiErrorPayload } from "@/types/api";

function resolveApiUrl() {
  const configured = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  const pointsToLocalhost = configured && /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/i.test(configured);
  if (process.env.NODE_ENV === "production" && (!configured || pointsToLocalhost)) return "/api/v1";
  return configured ?? "http://localhost:8000/api/v1";
}

const API_URL = resolveApiUrl();

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message);
    this.name = "ApiError";
    this.status = status;
    this.code = payload.code;
    this.details = payload.details;
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(503, {
      code: "API_UNAVAILABLE",
      message: "AthleteOS could not reach the API. Please try again in a moment.",
    });
  }
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, payload ?? { code: "REQUEST_FAILED", message: "The request could not be completed." });
  }
  return payload as T;
}

export function todayIso() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function formatNumber(value: number | null | undefined, maximumFractionDigits = 1) {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits }).format(value);
}
