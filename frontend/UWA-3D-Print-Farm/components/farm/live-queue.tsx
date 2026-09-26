"use client";

import { useState } from "react";
import { Pause, Play } from "lucide-react";
import { api, type QueueTile } from "@/lib/api/client";
import { formatDuration, formatWhen, jobStatusLabel, PRINTER_LABELS } from "@/lib/api/format";
import { usePolled } from "./use-polled";

const POLL_MS = 5000;

type Props = { role: "student" | "farmer" | "admin"; view: string };

const COPY: Record<string, string> = {
  "My jobs": "Your active jobs with estimated start and completion times, then your print history.",
  Jobs: "Every active job across the farm, then recent print history.",
  "Shared queue": "The current queue, in order, with the printer, estimated start and completion time for each job.",
  "Farm operations": "Printer status and the live queue.",
};

export function LiveQueue({ role, view }: Props) {
  const queue = usePolled(api.queue, POLL_MS);
  const history = usePolled(api.history, POLL_MS * 3);
  const printers = usePolled(api.printers, POLL_MS);
  const showPrinters = view === "Farm operations" || view === "Shared queue";
  const canControl = role !== "student";
  const [busyJob, setBusyJob] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const error = queue.error ?? history.error;

  /** The printer takes the command now; the queue shows the new state after the next printer poll (~2 s). */
  async function control(job: QueueTile) {
    setBusyJob(job.job_id);
    setActionError("");
    try {
      await (job.paused ? api.resumeJob(job.job_id) : api.pauseJob(job.job_id));
      await new Promise((resolve) => setTimeout(resolve, 2500));
      await queue.reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not reach the printer.");
    } finally {
      setBusyJob(null);
    }
  }

  return (
    <>
      <div className="heading">
        <div>
          <span>{role === "student" ? "Student" : role === "farmer" ? "Printer Farmer" : "Administrator"} portal</span>
          <h1>{view}</h1>
          <p>{COPY[view]}</p>
        </div>
      </div>
      {(error || actionError) && <div className="error farm-banner">{actionError || error?.message}</div>}

      {showPrinters && (
        <div className="farm-printers">
          {(printers.data ?? []).map((p) => (
            <section className="panel farm-printer-card" key={p.id}>
              <em className={`p-${p.status}`}>{PRINTER_LABELS[p.status]}</em>
              <h2>{p.model}</h2>
              <small>{p.location} · bed {p.bed_size}</small>
              <small>{p.current_material ? `${p.current_material.name}` : "No material recorded"}</small>
            </section>
          ))}
        </div>
      )}

      <section className="panel farm-table-panel">
        <h2>Queue</h2>
        <div className="farm-scroll">
          <table className="farm-table">
            <thead>
              <tr><th>File</th><th>Department</th><th>Printer</th><th>Status</th><th>Duration</th><th>Est. start</th><th>Est. completion</th>{canControl && <th>Actions</th>}</tr>
            </thead>
            <tbody>
              {(queue.data ?? []).map((j) => (
                <tr key={j.job_id}>
                  <td>{j.filename}</td>
                  <td>{j.department ?? "—"}</td>
                  <td>{j.assigned_printer ? `${j.assigned_printer.model}` : "Awaiting printer"}</td>
                  <td>{j.paused ? <em className="s-paused">Paused</em> : <em className={`s-${j.status}`}>{jobStatusLabel(j.status)}</em>}</td>
                  <td>{j.est_duration_formatted}{j.duration_is_default ? " (assumed)" : ""}</td>
                  <td>{formatWhen(j.est_start_time)}</td>
                  <td>{formatWhen(j.est_completion_time)}</td>
                  {canControl && (
                    <td>
                      {j.status === "printing" && (
                        <button className="farm-control" onClick={() => void control(j)} disabled={busyJob !== null}>
                          {j.paused ? <><Play />Resume</> : <><Pause />Pause</>}
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {queue.data && queue.data.length === 0 && <tr><td colSpan={canControl ? 8 : 7} className="farm-empty">The queue is empty.</td></tr>}
              {queue.loading && <tr><td colSpan={canControl ? 8 : 7} className="farm-empty">Loading…</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel farm-table-panel">
        <h2>History</h2>
        <div className="farm-scroll">
          <table className="farm-table">
            <thead>
              <tr><th>File</th><th>Printer</th><th>Material</th><th>Status</th><th>Print time</th><th>Filament</th><th>Cost</th><th>Finished</th></tr>
            </thead>
            <tbody>
              {(history.data ?? []).filter((j) => j.status !== "queued" && j.status !== "submitted" && j.status !== "printing").map((j) => (
                <tr key={j.job_id}>
                  <td>{j.filename}</td>
                  <td>{j.printer_model ?? "—"}</td>
                  <td>{j.material_name ?? "—"}</td>
                  <td><em className={`s-${j.status}`}>{jobStatusLabel(j.status)}</em></td>
                  <td>{formatDuration(j.actual_duration_min ?? j.est_duration_min)}</td>
                  <td>{(j.actual_filament_g ?? j.est_filament_g) != null ? `${(j.actual_filament_g ?? j.est_filament_g)!.toFixed(1)} g` : "—"}</td>
                  <td>${j.calculated_cost_usd.toFixed(2)}</td>
                  <td>{formatWhen(j.completed_at)}</td>
                </tr>
              ))}
              {history.data && history.data.filter((j) => j.status !== "queued" && j.status !== "submitted" && j.status !== "printing").length === 0 && (
                <tr><td colSpan={8} className="farm-empty">No finished jobs yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
