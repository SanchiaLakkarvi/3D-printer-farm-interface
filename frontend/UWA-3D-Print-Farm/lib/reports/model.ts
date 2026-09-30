import { z } from "zod";

// Match PR #115 exactly. Runtime validation prevents malformed API responses
// from becoming plausible-looking (but incorrect) zeroes in a dashboard.
const amount = z.number().finite().nonnegative();
const count = amount.int();
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine(value => Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value);
const seriesPoint = z.object({ date: isoDate, count: amount });
const totals = { total_jobs: count, completed_jobs: count, failed_jobs: count,
  total_print_hours: amount, total_filament_g: amount };
export const schemas = {
  usage: z.object({ ...totals, cancelled_jobs: count, active_queued_jobs: count,
    success_rate_pct: amount, avg_print_duration_min: amount,
    jobs_over_time: z.array(seriesPoint),
    status_breakdown: z.array(z.object({ status: z.string(), count })) }),
  printers: z.array(z.object({ ...totals, printer_id: z.string(), model: z.string(),
    location: z.string().nullable(), status: z.string(), utilization_pct: amount, queue_length: count })),
  materials: z.object({ materials: z.array(z.object({ material_id: z.string(), material_name: z.string(),
    type: z.string(), colour: z.string(), total_jobs: count, total_filament_g: amount })),
    filament_over_time: z.array(seriesPoint) }),
  users: z.array(z.object({ ...totals, user_id: z.string(), first_name: z.string(), last_name: z.string(),
    email: z.string(), student_number: z.string().nullable(), department: z.string().nullable(), role: z.string() })),
  departments: z.array(z.object({ ...totals, department: z.string() })),
};
export type ReportKey = keyof typeof schemas;
export type Reports = { [K in ReportKey]: z.infer<(typeof schemas)[K]> };
export const REPORT_KEYS: ReportKey[] = ["usage", "printers", "materials", "users", "departments"];
export type Filters = { from: string; to: string; printer_id: string; material_id: string;
  department: string; user_id: string; status: string };
export const blankFilters: Filters = { from: "", to: "", printer_id: "", material_id: "", department: "", user_id: "", status: "" };

/** Dates use UTC consistently with the backend's submitted_at daily buckets. */
export function recentFilters(days = 30, now = new Date()): Filters {
  const end = now.toISOString().slice(0, 10);
  const start = new Date(`${end}T00:00:00Z`);
  start.setUTCDate(start.getUTCDate() - days + 1);
  return { ...blankFilters, from: start.toISOString().slice(0, 10), to: end };
}
export function filterError(f: Filters): string | null {
  for (const value of [f.from, f.to]) {
    if (value && (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(Date.parse(value)) ||
      new Date(value).toISOString().slice(0, 10) !== value)) return "Choose valid start and end dates.";
  }
  return f.from && f.to && f.from > f.to ? "Start date must be on or before end date." : null;
}
export function reportQuery(f: Filters): string {
  const error = filterError(f);
  if (error) throw new Error(error);
  const params = new URLSearchParams();
  if (f.from) params.set("from_date", `${f.from}T00:00:00Z`);
  // FastAPI uses <=, so include the last microsecond of the end date.
  if (f.to) params.set("to_date", `${f.to}T23:59:59.999999Z`);
  for (const key of ["printer_id", "material_id", "department", "user_id", "status"] as const)
    if (f[key].trim()) params.set(key, f[key].trim());
  return params.toString();
}
export const number = (value: number, digits = 1) => new Intl.NumberFormat("en-AU", { maximumFractionDigits: digits }).format(value);
export const percent = (part: number, total: number): number | null => total > 0 ? part / total * 100 : null;
export const statusLabel = (value: string) => value === "removed" ? "Cancelled" : value.replaceAll("_", " ").replace(/^./, s => s.toUpperCase());

/** Insert missing days; long ranges become monthly to keep SVGs responsive.
 * The API series is grouped by submission date, not completion/consumption date.
 */
export function chartSeries(points: { date: string; count: number }[], f: Filters) {
  if (!points.length) return { rows: [], monthly: false };
  const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
  const start = f.from || sorted[0].date;
  const end = f.to || sorted[sorted.length - 1].date;
  const monthly = (Date.parse(end) - Date.parse(start)) / 86400000 > 180;
  const sums = new Map<string, number>();
  for (const point of sorted) {
    const key = monthly ? point.date.slice(0, 7) : point.date;
    sums.set(key, (sums.get(key) || 0) + point.count);
  }
  const cursor = new Date(`${monthly ? start.slice(0, 7) + "-01" : start}T00:00:00Z`);
  const last = monthly ? end.slice(0, 7) : end;
  const rows: { name: string; value: number }[] = [];
  // Cap pathological all-time ranges while retaining actual returned buckets.
  while (rows.length < 1200) {
    const name = cursor.toISOString().slice(0, monthly ? 7 : 10);
    if (name > last) return { rows, monthly };
    rows.push({ name, value: sums.get(name) || 0 });
    if (monthly) cursor.setUTCMonth(cursor.getUTCMonth() + 1);
    else cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return { rows: [...sums].sort(([a], [b]) => a.localeCompare(b)).map(([name, value]) => ({ name, value })), monthly };
}

/** CSV quoting also neutralises spreadsheet formulas in names/emails. */
export function csv(rows: (string | number | null)[][]): string {
  return "\uFEFF" + rows.map(row => row.map(value => {
    let text = String(value ?? "");
    if (typeof value === "string" && /^[\s]*[=+@-]|^[\t\r\n]/.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  }).join(",")).join("\r\n");
}
