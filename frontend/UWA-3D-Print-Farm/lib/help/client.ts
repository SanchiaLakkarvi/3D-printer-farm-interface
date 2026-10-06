/** Thin public FastAPI client for student troubleshooting chat. */

import { getApiBaseUrl } from "@/lib/auth/client";

export type HelpHistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type HelpChatResult = {
  message: string;
};

const HELP_GENERIC_ERROR = "Help chat is unavailable. Please try again later.";

export class HelpApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "HelpApiError";
    this.status = status;
    this.code = code;
  }
}

function readError(body: unknown): { message?: string; code?: string } {
  if (!body || typeof body !== "object") return {};
  const detail = (body as { detail?: unknown }).detail;
  if (!detail || typeof detail !== "object") return {};
  const record = detail as { message?: unknown; code?: unknown };
  return {
    message: typeof record.message === "string" ? record.message : undefined,
    code: typeof record.code === "string" ? record.code : undefined,
  };
}

export async function sendHelpMessage(
  message: string,
  history: HelpHistoryMessage[] = [],
): Promise<HelpChatResult> {
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}/api/help/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });
  } catch {
    throw new HelpApiError(HELP_GENERIC_ERROR, 0);
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Use the stable fallback below; never show raw provider/server content.
  }
  if (!response.ok) {
    const error = readError(body);
    throw new HelpApiError(
      error.message ?? HELP_GENERIC_ERROR,
      response.status,
      error.code,
    );
  }
  if (
    !body ||
    typeof body !== "object" ||
    typeof (body as { message?: unknown }).message !== "string"
  ) {
    throw new HelpApiError(HELP_GENERIC_ERROR, response.status);
  }
  return body as HelpChatResult;
}
