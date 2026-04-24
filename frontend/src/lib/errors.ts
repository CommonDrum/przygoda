/**
 * Central error translator for API calls.
 *
 * Every network error becomes a `FriendlyError` with:
 *   - title: short plain-Polish description the user sees
 *   - hint: actionable next step ("spróbuj ponownie", "zmień opis", ...)
 *   - retryable: whether we should offer a retry button
 *   - code: machine-readable tag (same vocab as backend `errors.py`)
 *
 * The backend ships these fields already in the JSON response; this helper
 * handles the cases where it's missing (network down before response arrives,
 * old endpoint, etc.) by classifying on the client side.
 */

import axios, { type AxiosError } from "axios";

export interface FriendlyError {
  title: string;
  hint: string;
  retryable: boolean;
  code: string;
}

interface BackendErrorBody {
  code?: string;
  detail?: string;
  title?: string;
  hint?: string;
  retryable?: boolean;
}

const CLIENT_NETWORK: FriendlyError = {
  code: "CLIENT_NETWORK",
  title: "Brak połączenia z serwerem",
  hint: "Sprawdź internet lub VPN i spróbuj ponownie. Jeśli to się powtarza, serwer może być wyłączony.",
  retryable: true,
};

const CLIENT_UNAUTHORIZED: FriendlyError = {
  code: "CLIENT_UNAUTHORIZED",
  title: "Sesja wygasła",
  hint: "Zaloguj się ponownie.",
  retryable: false,
};

const CLIENT_UNKNOWN: FriendlyError = {
  code: "CLIENT_UNKNOWN",
  title: "Coś poszło nie tak",
  hint: "Spróbuj ponownie. Jeśli problem się powtarza, odśwież stronę.",
  retryable: true,
};

export function toFriendlyError(err: unknown): FriendlyError {
  if (!axios.isAxiosError(err)) {
    if (err instanceof Error) {
      return { ...CLIENT_UNKNOWN, hint: err.message };
    }
    return CLIENT_UNKNOWN;
  }

  const ax = err as AxiosError<BackendErrorBody>;

  // No response at all → network / DNS / CORS / timeout
  if (!ax.response) {
    if (ax.code === "ECONNABORTED" || ax.message?.toLowerCase().includes("timeout")) {
      return {
        code: "CLIENT_TIMEOUT",
        title: "Serwer nie odpowiedział na czas",
        hint: "Spróbuj ponownie — jeśli powtarza się, poczekaj minutę.",
        retryable: true,
      };
    }
    return CLIENT_NETWORK;
  }

  const status = ax.response.status;
  const body = ax.response.data;

  if (status === 401) return CLIENT_UNAUTHORIZED;

  // Backend already provides friendly fields — prefer them
  if (body && (body.title || body.detail)) {
    return {
      code: body.code || `HTTP_${status}`,
      title: body.title || body.detail || "Błąd",
      hint: body.hint || defaultHintForStatus(status),
      retryable: body.retryable ?? isRetryableStatus(status),
    };
  }

  return {
    code: `HTTP_${status}`,
    title: "Błąd serwera",
    hint: defaultHintForStatus(status),
    retryable: isRetryableStatus(status),
  };
}

function defaultHintForStatus(status: number): string {
  if (status === 409) return "Poczekaj aż trwająca operacja się skończy.";
  if (status === 429 || status === 503) return "Usługa chwilowo zajęta — spróbuj ponownie za chwilę.";
  if (status === 404) return "Odśwież stronę — obiekt mógł zostać usunięty.";
  if (status >= 500) return "Spróbuj ponownie. Jeśli się powtarza, odśwież stronę lub skontaktuj się z administratorem.";
  return "Spróbuj ponownie.";
}

function isRetryableStatus(status: number): boolean {
  return [408, 409, 429, 500, 502, 503, 504].includes(status);
}

/** One-line summary suitable for toasts: `Title — hint`. */
export function friendlyToString(err: FriendlyError): string {
  return err.hint ? `${err.title} — ${err.hint}` : err.title;
}

/**
 * Shared error-toast helper: converts any thrown value to a friendly message
 * and hands it to the toast system. Use this in every `.catch` so users see
 * the same Polish vocabulary everywhere.
 */
export function showErrorToast(
  addToast: (msg: string, kind: "error") => void,
  err: unknown,
): void {
  const friendly = toFriendlyError(err);
  addToast(friendlyToString(friendly), "error");
}
