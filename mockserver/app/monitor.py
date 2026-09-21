"""Live monitor for the mock printers: what the backend is sending, in real time.

    GET /monitor           a page that refreshes itself every second
    GET /control/requests  the JSON behind it

Status polls (every 2 s per printer) and the Digest login challenges would drown
everything else, so they are only counted. Real actions (upload, start, stop,
pause, resume) are listed one by one.
"""

from __future__ import annotations

import re
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

_PRUSALINK = re.compile(r"^/prusalink/(?P<printer>[^/]+)(?P<rest>/.*)$")
_QUIET_GETS = ("/api/version", "/api/v1/status", "/api/v1/job")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _describe(method: str, rest: str, headers: Any) -> str:
    size = headers.get("content-length")
    kb = f" ({int(size) / 1024:.0f} KB)" if size and size.isdigit() else ""
    name = rest.rsplit("/", 1)[-1]
    if method == "PUT" and "/api/v1/files/" in rest:
        start = " and START PRINT" if headers.get("print-after-upload") == "?1" else ""
        return f"Upload {name}{kb}{start}"
    if method == "POST" and "/api/v1/files/" in rest:
        return f"Start printing {name}"
    if method == "DELETE" and "/api/v1/job/" in rest:
        return "Stop job"
    if method == "PUT" and rest.endswith("/pause"):
        return "Pause job"
    if method == "PUT" and rest.endswith("/resume"):
        return "Resume job"
    return f"{method} {rest}"


class RequestLog:
    def __init__(self, max_events: int = 100) -> None:
        self.events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self.polls: dict[str, dict[str, Any]] = {}
        self.handshakes = 0

    def record(self, printer: str, method: str, rest: str, status: int, headers: Any) -> None:
        if status == 401:
            self.handshakes += 1  # first half of Digest login; the retry is the real call
            return
        if method == "GET" and rest in _QUIET_GETS:
            entry = self.polls.setdefault(printer, {"count": 0, "last": None})
            entry["count"] += 1
            entry["last"] = _now()
            return
        self.events.appendleft(
            {
                "time": _now(),
                "printer": printer,
                "method": method,
                "action": _describe(method, rest, headers),
                "status": status,
            }
        )

    def snapshot(self) -> dict[str, Any]:
        return {"polls": self.polls, "handshakes": self.handshakes, "events": list(self.events)}


def install_monitor(app: FastAPI) -> RequestLog:
    log = RequestLog()

    @app.middleware("http")
    async def _record(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        match = _PRUSALINK.match(request.url.path)
        if match:
            log.record(
                match.group("printer"), request.method, match.group("rest"),
                response.status_code, request.headers,
            )
        return response

    @app.get("/control/requests", tags=["monitor"])
    def requests_seen() -> dict[str, Any]:
        return log.snapshot()

    @app.get("/monitor", response_class=HTMLResponse, include_in_schema=False)
    def monitor() -> str:
        return MONITOR_HTML

    return log


MONITOR_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mock printers, live</title>
<style>
:root{--bg:#f2f5f8;--card:#fff;--ink:#0e2440;--mute:#6b7a8d;--line:#e0e6eb;--blue:#0a6fa8;--green:#0b7c59;--red:#ac312c;--amber:#97620c}
@media (prefers-color-scheme:dark){:root{--bg:#0d1520;--card:#15202e;--ink:#e6edf5;--mute:#8fa1b5;--line:#25354a;--blue:#4fb3e8;--green:#3ccf9b;--red:#ff8a80;--amber:#f2b84b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif;padding:20px}
h1{font:600 20px system-ui;margin:0 0 4px}.sub{color:var(--mute);font-size:12px;margin-bottom:16px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);margin-right:6px;animation:p 1s infinite}
@keyframes p{50%{opacity:.25}}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h2{margin:0;font-size:15px}.row{display:flex;justify-content:space-between;align-items:center;gap:8px}
.badge{font-size:11px;font-weight:700;padding:3px 9px;border-radius:99px;background:var(--line);color:var(--mute)}
.badge.PRINTING{background:#dff1fb;color:var(--blue)}.badge.FINISHED,.badge.READY,.badge.IDLE{background:#e3f6ee;color:var(--green)}
.badge.ERROR,.badge.ATTENTION,.badge.STOPPED{background:#fdeceb;color:var(--red)}.badge.PAUSED{background:#fff2d6;color:var(--amber)}
.file{margin:10px 0 6px;font:12px ui-monospace,monospace;word-break:break-all;color:var(--mute)}
.bar{height:10px;background:var(--line);border-radius:6px;overflow:hidden}.bar i{display:block;height:100%;background:var(--blue);transition:width .6s}
.meta{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px;font-size:12px;color:var(--mute)}.meta b{color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);padding:6px 8px;border-bottom:1px solid var(--line)}
td{padding:8px;border-bottom:1px solid var(--line)}tr.new td{animation:f 2s}@keyframes f{from{background:#ffe9a8}}
.ok{color:var(--green);font-weight:700}.bad{color:var(--red);font-weight:700}.mono{font-family:ui-monospace,monospace;font-size:12px}
.empty{color:var(--mute);padding:14px 8px}.err{color:var(--red)}
</style></head><body>
<h1><span class="dot"></span>Mock printers, live</h1>
<div class="sub">Refreshes every second. Below: what each mock printer is doing, and what the backend has sent to it.
<span id="conn"></span></div>
<div class="grid" id="printers"></div>
<div class="card"><div class="row"><h2>Requests received from the backend</h2><span class="sub" id="stats"></span></div>
<table><thead><tr><th>Time</th><th>Printer</th><th>What the backend asked</th><th>Reply</th></tr></thead><tbody id="events"></tbody></table></div>
<script>
const seen = new Set(); let first = true;
const t = iso => iso ? new Date(iso).toLocaleTimeString([], {hour12:false}) : "-";
const esc = s => String(s ?? "").replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
async function tick(){
  try{
    const [ps, rq] = await Promise.all([fetch("/control/printers").then(r=>r.json()), fetch("/control/requests").then(r=>r.json())]);
    document.getElementById("conn").textContent = "";
    document.getElementById("printers").innerHTML = ps.map(p => {
      const tool = (p.toolheads||[]).find(x=>x.slot===p.active_tool) || (p.toolheads||[])[0];
      const poll = (rq.polls||{})[p.id];
      return `<div class="card"><div class="row"><h2>${esc(p.id)}</h2><span class="badge ${esc(p.state)}">${esc(p.state)}</span></div>
      <div class="file">${p.current_file ? esc(p.current_file) : "no file"}</div>
      <div class="bar"><i style="width:${p.progress_percent||0}%"></i></div>
      <div class="meta"><span><b>${(p.progress_percent||0).toFixed(1)}%</b> done</span>
      <span>nozzle <b>${tool ? tool.temperature_c : "-"}&deg;C</b></span><span>bed <b>${p.temp_bed_c}&deg;C</b></span>
      <span>status polls <b>${poll ? poll.count : 0}</b> (last ${poll ? t(poll.last) : "-"})</span></div></div>`;
    }).join("");
    document.getElementById("stats").textContent = `${rq.handshakes} logins (Digest challenges)`;
    const rows = rq.events.map(e => {
      const key = e.time + e.printer + e.action; const isNew = !first && !seen.has(key); seen.add(key);
      return `<tr class="${isNew ? "new" : ""}"><td class="mono">${t(e.time)}</td><td class="mono">${esc(e.printer)}</td><td>${esc(e.action)}</td><td class="${e.status < 300 ? "ok" : "bad"}">${e.status}</td></tr>`;
    }).join("");
    document.getElementById("events").innerHTML = rows || '<tr><td colspan="4" class="empty">Nothing yet. Submit a job in the web app and it will appear here.</td></tr>';
    first = false;
  }catch(e){ document.getElementById("conn").innerHTML = ' <span class="err">Cannot reach the mock server.</span>'; }
}
tick(); setInterval(tick, 1000);
</script></body></html>
"""
