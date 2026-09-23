"use client";

import { Boxes, CheckCircle2, ChevronRight, Clock3, FileText, Printer as PrinterIcon, Upload } from "lucide-react";
import { api, type QueueTile } from "@/lib/api/client";
import { formatClock, formatDuration, formatWhen, jobStatusLabel, PRINTER_LABELS } from "@/lib/api/format";
import { usePolled } from "./use-polled";
import type { UserProfile } from "@/lib/auth/client";

type Props = {
  profile: UserProfile;
  role: "student" | "farmer" | "admin";
  upload: () => void;
  openJobs: () => void;
};

const POLL_MS = 5000;

function greeting(now = new Date()): string {
  const hour = now.getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

/** Minutes until the last queued job is expected to finish. */
function minutesUntilQueueClears(queue: QueueTile[], now = Date.now()): number | null {
  const ends = queue.map((j) => (j.est_completion_time ? Date.parse(j.est_completion_time) : NaN)).filter((t) => !Number.isNaN(t));
  return ends.length ? Math.max(0, (Math.max(...ends) - now) / 60000) : null;
}

function Stat({ icon: Icon, value, label }: { icon: typeof FileText; value: string; label: string }) {
  return (
    <div className="stat">
      <i><Icon /></i>
      <span><b>{value}</b><small>{label}</small></span>
    </div>
  );
}

export function LiveDashboard({ profile, role, upload, openJobs }: Props) {
  const queue = usePolled(api.queue, POLL_MS);
  const history = usePolled(api.history, POLL_MS * 3);
  const printers = usePolled(api.printers, POLL_MS);

  const active = queue.data ?? [];
  const finished = history.data ?? [];
  const usable = (printers.data ?? []).filter((p) => p.status === "idle" || p.status === "printing");
  const clears = minutesUntilQueueClears(active);
  const recent = [
    ...active.map((j) => ({ id: j.job_id, name: j.filename, printer: j.assigned_printer?.model ?? "Awaiting printer", status: j.status, note: j.est_completion_time ? `done ~${formatClock(j.est_completion_time)}` : "" })),
    ...finished.filter((j) => !active.some((a) => a.job_id === j.job_id)).slice(0, 5).map((j) => ({ id: j.job_id, name: j.filename, printer: j.printer_model ?? "—", status: j.status, note: j.completed_at ? formatWhen(j.completed_at) : "" })),
  ].slice(0, 6);
  const failed = queue.error ?? history.error ?? printers.error;

  return (
    <>
      <div className="heading">
        <div>
          <span>{role === "student" ? "Student" : role === "farmer" ? "Printer Farmer" : "Administrator"} portal</span>
          <h1>{greeting()}, {profile.first_name}</h1>
          <p>{role === "student" ? "Here’s what’s happening with your print jobs." : "Here’s the latest activity across the Print Farm."}</p>
        </div>
        <button onClick={upload}><Upload />Upload new file</button>
      </div>
      {failed && <div className="error farm-banner">{failed.message}</div>}
      <div className="stats">
        <Stat icon={FileText} value={String(active.length)} label="Active jobs" />
        <Stat icon={Clock3} value={clears == null ? "—" : formatDuration(clears)} label="Until queue clears" />
        <Stat icon={CheckCircle2} value={String(finished.filter((j) => j.status === "completed").length)} label="Completed" />
        <Stat icon={PrinterIcon} value={`${usable.length} / ${printers.data?.length ?? 0}`} label="Printers online" />
      </div>
      <div className="dashgrid">
        <section className="panel">
          <h2>{role === "student" ? "Your recent jobs" : "Recent print activity"}</h2>
          {recent.length === 0 && <p className="farm-empty">{queue.loading ? "Loading…" : "No jobs yet. Upload a G-code file to get started."}</p>}
          {recent.map((j) => (
            <div className="job" key={j.id}>
              <i><Boxes /></i>
              <span><b>{j.name}</b><small>{j.printer}{j.note ? ` · ${j.note}` : ""}</small></span>
              <em className={`s-${j.status}`}>{jobStatusLabel(j.status)}</em>
              <ChevronRight />
            </div>
          ))}
        </section>
        <section className="panel quick">
          <h2>Printers</h2>
          {(printers.data ?? []).map((p) => (
            <div className="farm-printer" key={p.id}>
              <b>{p.model}</b>
              <small>{p.location}</small>
              <em className={`p-${p.status}`}>{PRINTER_LABELS[p.status]}</em>
            </div>
          ))}
          <button onClick={openJobs}><i><FileText /></i><b>{role === "student" ? "View my jobs" : "View all jobs"}</b><ChevronRight /></button>
        </section>
      </div>
    </>
  );
}
