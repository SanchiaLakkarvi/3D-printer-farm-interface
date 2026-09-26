"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Bell, CheckCircle2, PackageCheck, Pause, Play, Printer } from "lucide-react";
import { api, type AppNotification, type NotificationType } from "@/lib/api/client";
import { formatWhen } from "@/lib/api/format";
import { usePolled } from "./use-polled";

const POLL_MS = 5000;
/** Fired after marking read so the header badge updates without waiting for its next poll. */
const CHANGED = "farm:notifications-changed";

const ICONS: Record<NotificationType, typeof Bell> = {
  job_started: Printer,
  job_completed: CheckCircle2,
  job_error: AlertTriangle,
  ready_for_collection: PackageCheck,
  job_paused: Pause,
  job_resumed: Play,
};

const TITLES: Record<NotificationType, string> = {
  job_started: "Print started",
  job_completed: "Print finished",
  job_error: "Print failed",
  ready_for_collection: "Ready to collect",
  job_paused: "Print paused",
  job_resumed: "Print resumed",
};

function useOnChanged(reload: () => Promise<void>) {
  useEffect(() => {
    const handler = () => void reload();
    window.addEventListener(CHANGED, handler);
    return () => window.removeEventListener(CHANGED, handler);
  }, [reload]);
}

const announceChanged = () => window.dispatchEvent(new Event(CHANGED));

/** Header bell with the unread count; opens the Notifications page. */
export function NotificationBell({ open }: { open: () => void }) {
  const unread = usePolled(api.unreadCount, POLL_MS);
  useOnChanged(unread.reload);
  const count = unread.data?.count ?? 0;
  const label = count === 0 ? "Notifications" : `Notifications, ${count} unread`;
  return (
    <button className="farm-bell" onClick={open} aria-label={label} title={label}>
      <Bell />
      {count > 0 && <b>{count > 99 ? "99+" : count}</b>}
    </button>
  );
}

type Props = { role: "student" | "farmer" | "admin" };

export function LiveNotifications({ role }: Props) {
  const list = usePolled(api.notifications, POLL_MS);
  useOnChanged(list.reload);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const items = list.data ?? [];
  const unread = items.filter((n) => !n.is_read).length;

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setActionError("");
    try {
      await action();
      announceChanged();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not update notifications.");
    } finally {
      setBusy(false);
    }
  }

  const markRead = (n: AppNotification) => { if (!n.is_read) void run(() => api.markRead(n.id)); };

  return (
    <>
      <div className="heading">
        <div>
          <span>{role === "student" ? "Student" : role === "farmer" ? "Printer Farmer" : "Administrator"} portal</span>
          <h1>Notifications</h1>
          <p>Updates on your print jobs: when they start, pause, resume, finish or fail. New messages appear here automatically.</p>
        </div>
        {unread > 0 && <button onClick={() => void run(api.markAllRead)} disabled={busy}><CheckCircle2 />Mark all as read</button>}
      </div>
      {(list.error || actionError) && <div className="error farm-banner">{actionError || list.error?.message}</div>}

      <section className="panel">
        <h2>{unread > 0 ? `${unread} unread` : "All caught up"}</h2>
        {list.loading && <div className="farm-empty">Loading…</div>}
        {list.data && items.length === 0 && <div className="farm-empty">No notifications yet. Submit a print job and updates will show up here.</div>}
        <ul className="farm-notes">
          {items.map((n) => {
            const Icon = ICONS[n.type] ?? Bell;
            return (
              <li key={n.id}>
                <button className={`t-${n.type}${n.is_read ? "" : " unread"}`} onClick={() => markRead(n)} disabled={busy}>
                  <i><Icon /></i>
                  <span>
                    <b>{TITLES[n.type] ?? "Update"}</b>
                    <small>{n.message}</small>
                  </span>
                  <time dateTime={n.sent_at}>{formatWhen(n.sent_at)}</time>
                </button>
              </li>
            );
          })}
        </ul>
      </section>
    </>
  );
}
