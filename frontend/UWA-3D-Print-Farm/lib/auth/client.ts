/**
 * Thin FastAPI auth client. Mock `fetch` in unit tests; do not call real backends.
 */

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

export async function signupStudent(
  input: StudentSignupInput,
): Promise<UserProfile> {
  const url = `${getApiBaseUrl()}/api/auth/signup`;
  let response: Response;
  try {
    response = await fetch(url, {
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
  } catch {
    throw new AuthApiError(GENERIC_ERROR, 0);
  }

  const body = await parseJsonSafe(response);
  if (!response.ok) {
    const { message, code } = readErrorPayload(body);
    throw new AuthApiError(message ?? GENERIC_ERROR, response.status, code);
  }

  return body as UserProfile;
}
