import type { JobStatus, PrinterStatus } from "@/lib/api/client";

export function formatDuration(minutes: number | null | undefined): string {
  if (minutes == null || minutes <= 0) return "—";
  const total = Math.round(minutes);
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h === 0) return `${m}m`;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

export function formatClock(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** "4:32 PM" today, otherwise "Mon 4:32 PM". */
export function formatWhen(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (date.toDateString() === now.toDateString()) return formatClock(iso);
  return `${date.toLocaleDateString([], { weekday: "short" })} ${formatClock(iso)}`;
}

export function formatCost(usd: number): string {
  return `$${usd.toFixed(2)}`;
}

const JOB_LABELS: Record<JobStatus, string> = {
  submitted: "Submitted",
  queued: "In queue",
  printing: "Printing",
  completed: "Completed",
  failed: "Failed",
  removed: "Removed",
  ready_for_collection: "Ready to collect",
};

export const jobStatusLabel = (status: JobStatus): string => JOB_LABELS[status] ?? status;

export const PRINTER_LABELS: Record<PrinterStatus, string> = {
  idle: "Available",
  printing: "Printing",
  error: "Error",
  offline: "Offline",
  maintenance: "Maintenance",
};

/** A printer can take new jobs unless it is broken, offline or in maintenance. */
export const printerAcceptsJobs = (status: PrinterStatus): boolean =>
  status === "idle" || status === "printing";
