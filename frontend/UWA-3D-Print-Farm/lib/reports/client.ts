import { getApiBaseUrl } from "@/lib/auth/client";
import { getAccessToken } from "@/lib/auth/session";
import { schemas, reportQuery, type Filters, type ReportKey, type Reports } from "./model";

export class ReportError extends Error {
  constructor(message: string, readonly status = 0) { super(message); this.name = "ReportError"; }
}

/** Reuse the project's real bearer token; never supply a demo role or token.
 * Each request can be cancelled when filters change or the user leaves the page.
 */
export async function fetchReport<K extends ReportKey>(key: K, filters: Filters, signal: AbortSignal): Promise<Reports[K]> {
  const token = getAccessToken();
  if (!token) throw new ReportError("Your session has expired. Please sign in again.", 401);
  const base = getApiBaseUrl();
  let response: Response;
  try {
    response = await fetch(`${base}/api/reports/${key}?${reportQuery(filters)}`, {
      signal, cache: "no-store", headers: { Authorization: `Bearer ${token}` },
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ReportError("Cannot reach the reporting server. Check that the backend is running.");
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "Your session has expired. Please sign in again.",
      403: "Usage reports require a Farmer or Administrator account.",
      404: "Reporting endpoints are unavailable. Run the backend from PR #115.",
      422: "The server rejected these filters. Check the dates and selected values.",
    };
    throw new ReportError(messages[response.status] || `Report could not load (HTTP ${response.status}). Try again.`, response.status);
  }
  const body: unknown = await response.json().catch(() => null);
  const result = schemas[key].safeParse(body);
  if (!result.success) throw new ReportError("The server returned an unexpected report format. Check backend/frontend versions.");
  return result.data as Reports[K];
}
