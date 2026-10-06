"""Live monitor for the mock printers, styled like a Prusa Connect farm dashboard.

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
<title>Mock Printer Farm</title>
<style>
:root{--bg:#f4f4f4;--card:#fff;--ink:#1a1919;--mute:#6f6f6f;--line:#e2e2e2;--bar:#1a1919;--bar-ink:#fff;--accent:#fa6831;--track:#ececec;
--s-printing:#fa6831;--s-paused:#e8a317;--s-finished:#33a852;--s-ready:#3e8ed0;--s-idle:#8a8a8a;--s-busy:#7a5af8;--s-error:#e5383b;--s-attention:#d9480f;--s-stopped:#555}
:root:not([data-theme="light"]){color-scheme:light dark}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121212;--card:#1e1e1e;--ink:#ececec;--mute:#9a9a9a;--line:#2e2e2e;--bar:#0a0a0a;--track:#2c2c2c}}
:root[data-theme="dark"]{--bg:#121212;--card:#1e1e1e;--ink:#ececec;--mute:#9a9a9a;--line:#2e2e2e;--bar:#0a0a0a;--track:#2c2c2c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 "Helvetica Neue",Arial,system-ui,sans-serif}
header{background:var(--bar);color:var(--bar-ink);display:flex;align-items:center;gap:14px;padding:0 20px;height:56px;position:sticky;top:0;z-index:5}
.logo{display:flex;align-items:center;gap:10px;font-weight:700;letter-spacing:.02em}
.logo i{width:26px;height:26px;border-radius:6px;background:var(--accent);display:grid;place-items:center}
.logo small{font-weight:400;opacity:.6;margin-left:4px}
.mockpill{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;border:1px solid rgba(255,255,255,.35);border-radius:4px;padding:2px 7px}
.live{margin-left:auto;font-size:12px;opacity:.8;display:flex;align-items:center;gap:6px}
.live b{width:8px;height:8px;border-radius:50%;background:#33a852;animation:p 1.2s infinite}.live.off b{background:#e5383b;animation:none}
@keyframes p{50%{opacity:.3}}
.layout{display:flex;min-height:calc(100vh - 56px)}
nav{width:200px;flex:none;background:var(--card);border-right:1px solid var(--line);padding:16px 0}
nav a{display:flex;align-items:center;gap:10px;padding:10px 20px;color:var(--ink);text-decoration:none;font-weight:600;border-left:3px solid transparent}
nav a.on{border-left-color:var(--accent);background:var(--bg)}nav a span{margin-left:auto;font-size:11px;color:var(--mute);font-weight:400}
main{flex:1;min-width:0;padding:20px 24px 40px}
h1{font-size:22px;margin:0 0 2px}.sub{color:var(--mute);font-size:13px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer;display:flex;align-items:center;gap:6px}
.chip.on{border-color:var(--ink);font-weight:700}.chip i{width:8px;height:8px;border-radius:50%}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden;cursor:pointer;text-align:left;font:inherit;color:inherit;padding:0;display:flex;flex-direction:column;transition:box-shadow .15s}
.tile:hover,.tile.sel{box-shadow:0 0 0 2px var(--accent)}
.band{color:#fff;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:7px 14px;display:flex;justify-content:space-between}
.band span{font-weight:400;opacity:.9;text-transform:none;letter-spacing:0}
.tbody{padding:14px;display:grid;grid-template-columns:88px 1fr;gap:14px;align-items:center}
.pic{width:88px;height:88px;border-radius:6px;background:var(--bg);display:grid;place-items:center;color:var(--mute)}
.name{font-weight:700;font-size:15px}.model{color:var(--mute);font-size:12px}
.file{font-size:12px;color:var(--mute);margin-top:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.prog{padding:0 14px}.track{height:6px;background:var(--track);border-radius:3px;overflow:hidden}.track i{display:block;height:100%;transition:width .6s}
.pnums{display:flex;justify-content:space-between;font-size:12px;color:var(--mute);margin-top:6px}.pnums b{color:var(--ink)}
.temps{display:flex;border-top:1px solid var(--line);margin-top:12px}
.temps div{flex:1;padding:9px 6px;text-align:center;border-right:1px solid var(--line)}.temps div:last-child{border-right:0}
.temps small{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute)}.temps b{font-size:14px}
.tools{display:flex;gap:6px;flex-wrap:wrap;padding:10px 14px;border-top:1px solid var(--line)}
.tool{display:flex;align-items:center;gap:5px;font-size:11px;border:1px solid var(--line);border-radius:4px;padding:2px 6px}
.tool.act{border-color:var(--accent)}.spool{width:10px;height:10px;border-radius:50%;border:1px solid rgba(128,128,128,.6)}
.foot{font-size:11px;color:var(--mute);padding:8px 14px;border-top:1px solid var(--line);margin-top:auto}
.panel{background:var(--card);border:1px solid var(--line);border-radius:8px;margin-top:20px}
.phead{display:flex;align-items:center;gap:12px;padding:14px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.phead h2{margin:0;font-size:16px}.phead .x{margin-left:auto;background:none;border:1px solid var(--line);color:var(--ink);border-radius:4px;padding:4px 10px;cursor:pointer;font:inherit}
.tele{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));border-bottom:1px solid var(--line)}
.tele div{padding:12px 16px;border-right:1px solid var(--line)}.tele small{display:block;font-size:11px;color:var(--mute);text-transform:uppercase;letter-spacing:.05em}.tele b{font-size:18px}
.job{display:grid;grid-template-columns:120px 1fr;gap:18px;padding:16px;align-items:center}
.ring{width:120px;height:120px}.ring text{font:700 22px "Helvetica Neue",Arial,sans-serif;fill:var(--ink)}
dl{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;margin:0;font-size:13px}dt{color:var(--mute)}dd{margin:0;font-weight:600;word-break:break-all}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);padding:8px 16px;border-bottom:1px solid var(--line)}
td{padding:9px 16px;border-bottom:1px solid var(--line)}tr:last-child td{border-bottom:0}
tr.new td{animation:f 2s}@keyframes f{from{background:rgba(250,104,49,.25)}}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px}
.act-ic{display:inline-flex;width:22px;height:22px;border-radius:50%;align-items:center;justify-content:center;color:#fff;font-size:11px;margin-right:8px;vertical-align:middle}
.ok{color:var(--s-finished);font-weight:700}.bad{color:var(--s-error);font-weight:700}
.empty{color:var(--mute);padding:16px}
.scroll{overflow-x:auto}
@media (max-width:760px){nav{display:none}main{padding:16px}header{padding:0 16px}.logo small{display:none}.job{grid-template-columns:1fr;justify-items:center}}
</style></head><body>
<header>
  <div class="logo"><i><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><path d="M4 20h16M7 20V8l5-4 5 4v12"/></svg></i>Print Farm<small>Connect-style view</small></div>
  <span class="mockpill">Mock</span>
  <span class="live" id="live"><b></b><span id="livetxt">Live</span></span>
</header>
<div class="layout">
<nav>
  <a href="#printers" class="on">Printers <span id="navcount"></span></a>
  <a href="#events">Events <span id="navevents"></span></a>
</nav>
<main>
  <section id="printers">
    <h1>Printers</h1>
    <div class="sub">Simulated Prusa printers, answering the backend through the PrusaLink API. Refreshes every second. Click a printer for details.</div>
    <div class="chips" id="chips"></div>
    <div class="grid" id="grid"></div>
    <div id="detail"></div>
  </section>
  <section id="events" class="panel">
    <div class="phead"><h2>Events from the backend</h2><span class="sub" id="stats"></span></div>
    <div class="scroll"><table><thead><tr><th>Time</th><th>Printer</th><th>Action</th><th>Reply</th></tr></thead><tbody id="events-body"></tbody></table></div>
  </section>
</main>
</div>
<script>
const STATE_GROUPS = [["ALL","All"],["PRINTING","Printing"],["PAUSED","Paused"],["READY","Ready / idle"],["FINISHED","Finished"],["ERROR","Error / attention"]];
const GROUP_OF = {IDLE:"READY",READY:"READY",BUSY:"READY",STOPPED:"FINISHED",ATTENTION:"ERROR"};
const MODELS = {PRUSA_CORE_ONE:"Prusa CORE One",PRUSA_XL_5T_INPUT_SHAPER:"Prusa XL 5-toolhead"};
let filter = "ALL", selected = null, first = true, last = {ps:[],rq:{events:[],polls:{}}};
const seen = new Set();
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const clock = iso => iso ? new Date(iso).toLocaleTimeString([], {hour12:false}) : "-";
const dur = s => { if (s == null) return "-"; s = Math.max(0, Math.round(s)); const h = Math.floor(s/3600), m = Math.floor(s%3600/60); return h ? h+"h "+m+"m" : m ? m+"m "+(s%60)+"s" : s+"s"; };
const stateVar = st => "var(--s-" + (st||"idle").toLowerCase() + ", var(--s-idle))";
const group = st => GROUP_OF[st] || st;
const deg = (v, t) => v == null ? "-" : Math.round(v) + (t ? "/" + Math.round(t) : "") + "&deg;";
const tool = p => (p.toolheads||[]).find(x => x.slot === p.active_tool) || (p.toolheads||[])[0];
const picture = p => p.physical_model === "PRUSA_XL_5T_INPUT_SHAPER"
  ? '<svg width="60" height="60" viewBox="0 0 60 60" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="48" height="48" rx="3"/><path d="M6 16h48M14 50h32"/><g stroke-width="1.5"><path d="M15 10v3M23 10v3M31 10v3M39 10v3M47 10v3"/></g><rect x="26" y="20" width="8" height="8"/></svg>'
  : '<svg width="60" height="60" viewBox="0 0 60 60" fill="none" stroke="currentColor" stroke-width="2"><rect x="10" y="6" width="40" height="48" rx="3"/><rect x="15" y="12" width="30" height="30" rx="1" stroke-width="1.5"/><path d="M15 22h30"/><rect x="27" y="18" width="6" height="6"/><path d="M18 48h24"/></svg>';
function actionIcon(text) {
  const [ic, v] = /START PRINT|^Start/.test(text) ? ["&#9654;", "printing"] : text.startsWith("Upload") ? ["&#8679;", "ready"]
    : text.startsWith("Pause") ? ["&#10074;&#10074;", "paused"] : text.startsWith("Resume") ? ["&#9654;", "finished"]
    : text.startsWith("Stop") ? ["&#9632;", "error"] : ["&#8226;", "idle"];
  return `<span class="act-ic" style="background:var(--s-${v})">${ic}</span>`;
}
function tileHtml(p, polls) {
  const t = tool(p), poll = polls[p.id], pct = p.progress_percent || 0, color = stateVar(p.state);
  const chamber = p.chamber_temperature_c != null ? `<div><small>Chamber</small><b>${deg(p.chamber_temperature_c)}</b></div>` : "";
  const tools = (p.toolheads||[]).length > 1 ? `<div class="tools">${p.toolheads.map(x => `<span class="tool ${x.slot===p.active_tool?"act":""}"><i class="spool" style="background:${esc(x.colour||"transparent")}"></i>T${x.slot+1} ${esc(x.material||"-")}</span>`).join("")}</div>`
    : t ? `<div class="tools"><span class="tool"><i class="spool" style="background:${esc(t.colour||"transparent")}"></i>${esc(t.material||"-")} &middot; ${t.nozzle_diameter_mm} mm${t.high_flow?" HF":""}</span></div>` : "";
  return `<button class="tile ${selected===p.id?"sel":""}" data-id="${esc(p.id)}">
    <div class="band" style="background:${color}">${esc(p.state)}<span>${p.state==="PRINTING"||p.state==="PAUSED" ? pct.toFixed(0)+"%" : ""}</span></div>
    <div class="tbody"><div class="pic">${picture(p)}</div><div><div class="name">${esc(p.id)}</div><div class="model">${esc(MODELS[p.physical_model]||p.physical_model)}</div>
    <div class="file" title="${esc(p.current_file||"")}">${p.current_file ? esc(p.current_file.split("/").pop()) : "No file loaded"}</div></div></div>
    <div class="prog"><div class="track"><i style="width:${pct}%;background:${color}"></i></div>
    <div class="pnums"><span><b>${pct.toFixed(1)}%</b> done</span><span>Remaining <b>${dur(p.time_remaining_s)}</b></span></div></div>
    <div class="temps"><div><small>Nozzle</small><b>${deg(t&&t.temperature_c, t&&t.target_temperature_c)}</b></div><div><small>Bed</small><b>${deg(p.temp_bed_c, p.target_bed_c)}</b></div>${chamber}</div>
    ${tools}
    <div class="foot">Status polls from backend: <b>${poll?poll.count:0}</b> &middot; last ${poll?clock(poll.last):"-"}</div></button>`;
}
function detailHtml(p, events) {
  const t = tool(p), pct = p.progress_percent || 0, color = stateVar(p.state), r = 52, c = 2*Math.PI*r;
  const mine = events.filter(e => e.printer === p.id).slice(0, 8);
  return `<div class="panel"><div class="phead"><h2>${esc(p.id)}</h2><span class="model">${esc(MODELS[p.physical_model]||p.physical_model)} &middot; PrusaLink dashboard</span><button class="x" id="close">Close</button></div>
  <div class="tele"><div><small>State</small><b style="color:${color}">${esc(p.state)}</b></div><div><small>Nozzle</small><b>${deg(t&&t.temperature_c, t&&t.target_temperature_c)}</b></div><div><small>Heatbed</small><b>${deg(p.temp_bed_c, p.target_bed_c)}</b></div>${p.chamber_temperature_c!=null?`<div><small>Chamber</small><b>${deg(p.chamber_temperature_c, p.chamber_target_c)}</b></div>`:""}<div><small>Active tool</small><b>${p.active_tool!=null?"T"+(p.active_tool+1):"-"}</b></div></div>
  <div class="job"><svg class="ring" viewBox="0 0 120 120"><circle cx="60" cy="60" r="${r}" fill="none" stroke="var(--track)" stroke-width="10"/><circle cx="60" cy="60" r="${r}" fill="none" stroke="${color}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c*(1-pct/100)}" transform="rotate(-90 60 60)"/><text x="60" y="67" text-anchor="middle">${pct.toFixed(0)}%</text></svg>
  <dl><dt>File</dt><dd>${p.current_file ? esc(p.current_file) : "-"}</dd><dt>Printing time</dt><dd>${dur(p.elapsed_s)}</dd><dt>Remaining</dt><dd>${dur(p.time_remaining_s)}</dd><dt>Estimated total</dt><dd>${dur(p.estimated_duration_s)}</dd>
  <dt>Material</dt><dd>${t ? esc((t.material||"-") + (t.colour?" ("+t.colour+")":"")) + (t.filament_remaining_g!=null?" &middot; "+Math.round(t.filament_remaining_g)+" g left":"") : "-"}</dd>
  <dt>File check</dt><dd>${p.last_validation ? (p.last_validation.valid ? '<span class="ok">Passed</span>' : '<span class="bad">Failed ('+p.last_validation.issues.length+' issues)</span>') : "-"}</dd></dl></div>
  <div class="scroll"><table><thead><tr><th>Time</th><th>Recent actions on this printer</th><th>Reply</th></tr></thead><tbody>${mine.map(e => `<tr><td class="mono">${clock(e.time)}</td><td>${actionIcon(e.action)}${esc(e.action)}</td><td class="${e.status<300?"ok":"bad"}">${e.status}</td></tr>`).join("") || '<tr><td colspan="3" class="empty">No actions yet.</td></tr>'}</tbody></table></div></div>`;
}
function render() {
  const {ps, rq} = last, polls = rq.polls || {};
  const counts = {ALL: ps.length}; ps.forEach(p => { const g = group(p.state); counts[g] = (counts[g]||0) + 1; });
  document.getElementById("chips").innerHTML = STATE_GROUPS.map(([k, label]) => `<button class="chip ${filter===k?"on":""}" data-f="${k}">${k!=="ALL"?`<i style="background:${stateVar(k)}"></i>`:""}${label} <b>${counts[k]||0}</b></button>`).join("");
  const shown = ps.filter(p => filter === "ALL" || group(p.state) === filter);
  document.getElementById("grid").innerHTML = shown.map(p => tileHtml(p, polls)).join("") || '<div class="empty">No printers in this state.</div>';
  const sel = ps.find(p => p.id === selected);
  document.getElementById("detail").innerHTML = sel ? detailHtml(sel, rq.events) : "";
  document.getElementById("navcount").textContent = ps.length;
  document.getElementById("navevents").textContent = rq.events.length;
  document.getElementById("stats").textContent = `${rq.handshakes||0} logins (Digest challenges) · status polls counted on each printer`;
  const rows = rq.events.map(e => {
    const key = e.time + e.printer + e.action, isNew = !first && !seen.has(key); seen.add(key);
    return `<tr class="${isNew?"new":""}"><td class="mono">${clock(e.time)}</td><td class="mono">${esc(e.printer)}</td><td>${actionIcon(e.action)}${esc(e.action)}</td><td class="${e.status<300?"ok":"bad"}">${e.status}</td></tr>`;
  }).join("");
  document.getElementById("events-body").innerHTML = rows || '<tr><td colspan="4" class="empty">Nothing yet. Submit a job in the web app and it will appear here.</td></tr>';
  first = false;
}
document.addEventListener("click", e => {
  const chip = e.target.closest(".chip"); if (chip) { filter = chip.dataset.f; render(); return; }
  if (e.target.closest("#close")) { selected = null; render(); return; }
  const tile = e.target.closest(".tile"); if (tile) { selected = selected === tile.dataset.id ? null : tile.dataset.id; render(); if (selected) document.getElementById("detail").scrollIntoView({behavior:"smooth", block:"nearest"}); }
});
async function tick() {
  const live = document.getElementById("live"), txt = document.getElementById("livetxt");
  try {
    const [ps, rq] = await Promise.all([fetch("/control/printers").then(r => r.json()), fetch("/control/requests").then(r => r.json())]);
    last = {ps, rq}; live.classList.remove("off"); txt.textContent = "Live"; render();
  } catch (err) { live.classList.add("off"); txt.textContent = "Cannot reach the mock server"; }
}
tick(); setInterval(tick, 1000);
</script></body></html>
"""
