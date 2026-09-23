/** Typed client for the FastAPI backend's job, printer and material endpoints. */

import { getApiBaseUrl } from "@/lib/auth/client";
import { getAccessToken } from "@/lib/auth/session";

export type JobStatus =
  | "submitted"
  | "queued"
  | "printing"
  | "completed"
  | "failed"
  | "removed"
  | "ready_for_collection";

export type PrinterStatus = "idle" | "printing" | "error" | "offline" | "maintenance";

export type QueueTile = {
  job_id: string;
  filename: string;
  status: JobStatus;
  assigned_printer: { id: string; model: string; location: string | null; status: PrinterStatus } | null;
  est_duration_min: number | null;
  est_duration_formatted: string;
  est_start_time: string | null;
  est_completion_time: string | null;
  duration_is_default: boolean;
  submitted_at: string;
};

export type HistoryItem = {
  job_id: string;
  filename: string;
  status: JobStatus;
  material_name: string | null;
  material_type: string | null;
  colour: string | null;
  printer_model: string | null;
  printer_location: string | null;
  est_duration_min: number | null;
  actual_duration_min: number | null;
  est_filament_g: number | null;
  actual_filament_g: number | null;
  calculated_cost_usd: number;
  submitted_at: string;
  completed_at: string | null;
};

export type Printer = {
  id: string;
  model: string;
  status: PrinterStatus;
  bed_size: string;
  location: string;
  current_material: { id: string; name: string; type: string; colour: string } | null;
};

export type Material = { id: string; name: string; type: string; colour: string };

export type ValidationStage = { stage: number; name: string; status: string };

export type GcodeValidation = {
  filename: string;
  passed: boolean;
  message: string;
  errors: string[];
  failed_stage: number | null;
  stages: ValidationStage[];
  required_material: string | null;
  est_duration_min: number | null;
  est_filament_g: number | null;
  estimated_cost_usd: number;
  compatible_printers: { printer_id: string; model: string; location: string | null; status: PrinterStatus }[];
};

export type JobSubmission = {
  job_id: string;
  filename: string;
  status: JobStatus;
  printer_id: string;
  est_duration_min: number;
  est_filament_g: number | null;
  estimated_cost_usd: number;
  est_start_time: string | null;
  est_completion_time: string | null;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly details: string[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Turn FastAPI's `{detail: {code, message, errors?}}` or validation-list errors into an ApiError. */
function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const d = detail as { code?: string; message?: string; errors?: string[] };
    return new ApiError(d.message ?? "Request failed.", status, d.code, d.errors ?? []);
  }
  if (Array.isArray(detail)) {
    const messages = detail.map((e) => (e as { msg?: string }).msg).filter((m): m is string => !!m);
    return new ApiError(messages[0] ?? "Request failed.", status, undefined, messages);
  }
  return new ApiError(typeof detail === "string" ? detail : "Request failed.", status);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Cannot reach the Print Farm server.", 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw toApiError(response.status, body);
  }
  return (await response.json()) as T;
}

function uploadForm(file: File, extra: Record<string, string> = {}): FormData {
  const form = new FormData();
  form.append("file", file);
  for (const [key, value] of Object.entries(extra)) form.append(key, value);
  return form;
}

export const api = {
  queue: () => request<QueueTile[]>("/jobs/queue"),
  history: () => request<HistoryItem[]>("/jobs/history"),
  printers: () => request<Printer[]>("/printers"),
  materials: () => request<Material[]>("/materials"),
  validate: (file: File) =>
    request<GcodeValidation>("/jobs/validate", { method: "POST", body: uploadForm(file) }),
  submit: (file: File, printerId: string, materialId: string) =>
    request<JobSubmission>("/jobs", {
      method: "POST",
      body: uploadForm(file, { printer_id: printerId, material_id: materialId }),
    }),
};
