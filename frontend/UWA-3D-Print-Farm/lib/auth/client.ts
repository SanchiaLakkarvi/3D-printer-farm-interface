/**
 * Thin FastAPI auth client. Mock `fetch` in unit tests; do not call real backends.
 */

import { clearAccessToken, getAccessToken, setAccessToken } from "./session";

const GENERIC_ERROR = "Something went wrong. Please try again.";

export { GENERIC_ERROR as AUTH_GENERIC_ERROR };

export type StudentSignupInput = {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  department: string;
};

export type UserProfile = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  department: string | null;
  student_number: string | null;
};

export type SignInResult = {
  access_token: string;
  token_type: string;
  user: UserProfile;
};

export const ROLE_MISMATCH_ERROR =
  "This account does not match the access option you selected.";

export class AuthApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.code = code;
  }
}

export function getApiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!base) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL is not set. Point it at the FastAPI origin (e.g. http://localhost:8000).",
    );
  }
  return base.replace(/\/$/, "");
}

/** Map department dropdown selection; Other uses free-text as `department`. */
export function resolveDepartment(selected: string, otherText: string): string {
  if (selected === "Other") return otherText.trim();
  return selected.trim();
}

function readErrorPayload(body: unknown): { message?: string; code?: string } {
  if (!body || typeof body !== "object") return {};
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return { message: detail };
  if (detail && typeof detail === "object") {
    const record = detail as { message?: unknown; code?: unknown };
    return {
      message: typeof record.message === "string" ? record.message : undefined,
      code: typeof record.code === "string" ? record.code : undefined,
    };
  }
  return {};
}

async function parseJsonSafe(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

async function requestJson(
  path: string,
  init: RequestInit,
): Promise<{ response: Response; body: unknown }> {
  const url = `${getApiBaseUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new AuthApiError(GENERIC_ERROR, 0);
  }
  const body = await parseJsonSafe(response);
  if (!response.ok) {
    const { message, code } = readErrorPayload(body);
    throw new AuthApiError(message ?? GENERIC_ERROR, response.status, code);
  }
  return { response, body };
}

export async function signupStudent(
  input: StudentSignupInput,
): Promise<UserProfile> {
  const { body } = await requestJson("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      first_name: input.first_name,
      last_name: input.last_name,
      email: input.email,
      password: input.password,
      department: input.department,
    }),
  });
  return body as UserProfile;
}

export async function signIn(
  email: string,
  password: string,
): Promise<SignInResult> {
  const { body } = await requestJson("/api/auth/signin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return body as SignInResult;
}

export async function signInWithRoleMatch(
  email: string,
  password: string,
  expectedRole: string,
): Promise<UserProfile> {
  const result = await signIn(email, password);
  if (result.user.role !== expectedRole) {
    clearAccessToken();
    throw new AuthApiError(ROLE_MISMATCH_ERROR, 403, "ROLE_MISMATCH");
  }
  setAccessToken(result.access_token);
  return result.user;
}

export async function fetchMe(): Promise<UserProfile> {
  const token = getAccessToken();
  if (!token) {
    throw new AuthApiError(GENERIC_ERROR, 401, "NO_TOKEN");
  }
  const { body } = await requestJson("/api/auth/me", {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  return body as UserProfile;
}

/** Restore dashboard from sessionStorage token via `/me`. Skips Role-match. */
export async function restoreSession(): Promise<UserProfile | null> {
  const token = getAccessToken();
  if (!token) return null;
  try {
    return await fetchMe();
  } catch {
    clearAccessToken();
    return null;
  }
}

/** Clear local session; best-effort POST Sign-out (JWT is not revoked server-side). */
export async function signOut(): Promise<void> {
  const token = getAccessToken();
  clearAccessToken();
  if (!token) return;
  try {
    await fetch(`${getApiBaseUrl()}/api/auth/signout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    // Client discard is authoritative; network/server failures are ignored.
  }
}
