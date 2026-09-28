"use client";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Activity, ArrowDownToLine, RefreshCw, SlidersHorizontal } from "lucide-react";
import { fetchReport, ReportError } from "@/lib/reports/client";
import { chartSeries, csv, filterError, number, percent, recentFilters, REPORT_KEYS, statusLabel, type Filters, type ReportKey, type Reports } from "@/lib/reports/model";
import { ReportChart, ReportState } from "./report-charts";
import "./reports.css";

type Snapshot = { data: Partial<Reports>; errors: Partial<Record<ReportKey, string>>; loading: boolean; updated: Date | null };
const tabs = ["Overview", "Printers", "Materials", "Departments", "Users"] as const;
type Tab = typeof tabs[number];
const printerName = (p: Reports["printers"][number]) => `${p.model} · ${p.location || "No location"} · ${p.printer_id.slice(-6)}`;
// Match the registration choices; reports can also reveal departments entered via "Other".
const standardDepartments = ["Mechanical Engineering", "Electrical Engineering", "Civil Engineering", "Computer Science & Software Engineering", "Architecture & Design"];

/** The parent uses the authenticated profile, not the role selected on login.
 * Backend require_farmer remains the authority for every request.
 */
export function UsageReports({ role }: { role: string }) {
  return role === "admin" || role === "farmer" ? <ReportsDashboard /> : <div className="report-error" role="alert">Usage reports require a Farmer or Administrator account.</div>;
}

function ReportsDashboard() {
  const [filters, setFilters] = useState<Filters>(() => recentFilters());
  const [draft, setDraft] = useState<Filters>(() => recentFilters());
  const [formError, setFormError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [tab, setTab] = useState<Tab>("Overview");
  const [snapshot, setSnapshot] = useState<Snapshot>({ data: {}, errors: {}, loading: true, updated: null });
  const [catalog, setCatalog] = useState<{ printers: Reports["printers"]; materials: Reports["materials"]["materials"]; departments: string[] }>({ printers: [], materials: [], departments: [] });
  const [otherDepartment, setOtherDepartment] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("jobs");
  const [page, setPage] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let alive = true;
    // Event handlers clear old results before changing the request filters.
    const timer = window.setTimeout(() => {
      if (!alive) return;
      alive = false;
      controller.abort();
      setSnapshot({ data: {}, errors: Object.fromEntries(REPORT_KEYS.map(k => [k, "Reports took too long to load. Try Refresh."])), loading: false, updated: null });
    }, 25000);
    // Independent endpoints can fail without turning successful reports into zeroes.
    void Promise.allSettled(REPORT_KEYS.map(key => fetchReport(key, filters, controller.signal))).then(results => {
      if (!alive) return;
      window.clearTimeout(timer);
      const data: Partial<Reports> = {};
      const errors: Partial<Record<ReportKey, string>> = {};
      let accessError: string | null = null;
      results.forEach((result, index) => {
        const key = REPORT_KEYS[index];
        if (result.status === "fulfilled") Object.assign(data, { [key]: result.value });
        else {
          errors[key] = result.reason instanceof Error ? result.reason.message : "Unable to load this report.";
          if (result.reason instanceof ReportError && [401, 403].includes(result.reason.status)) accessError = errors[key]!;
        }
      });
      // Never retain sensitive rows if an endpoint says the session is unauthorised.
      if (accessError) {
        setCatalog({ printers: [], materials: [], departments: [] });
        setSnapshot({ data: {}, errors: Object.fromEntries(REPORT_KEYS.map(k => [k, accessError!])), loading: false, updated: null });
        return;
      }
      setCatalog(old => ({
        printers: data.printers ?? old.printers,
        materials: data.materials?.materials ?? old.materials,
        // Retain names after filtering, so narrowing a report never removes a selected option.
        // "General" also groups jobs with no department and cannot reliably filter those jobs.
        departments: [...new Set([...old.departments, ...(data.departments || []).map(row => row.department)])].filter(name => name && name !== "General"),
      }));
      setSnapshot({ data, errors, loading: false, updated: Object.keys(data).length ? new Date() : null });
    });
    return () => { alive = false; window.clearTimeout(timer); controller.abort(); };
  }, [filters, refresh]);

  const { data, errors, loading, updated } = snapshot;
  const departmentOptions = [...new Set([...standardDepartments, ...catalog.departments])];
  const showOtherDepartment = otherDepartment || Boolean(draft.department && !departmentOptions.includes(draft.department));
  const users = useMemo(() => {
    const query = search.toLocaleLowerCase().trim();
    return (data.users || []).filter(u => [u.first_name, u.last_name, u.email, u.student_number, u.department, u.role].join(" ").toLocaleLowerCase().includes(query)).sort((a, b) => {
      if (sort === "name") return `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
      const key = sort === "hours" ? "total_print_hours" : sort === "filament" ? "total_filament_g" : "total_jobs";
      return b[key] - a[key] || a.user_id.localeCompare(b.user_id);
    });
  }, [data.users, search, sort]);
  const pageCount = Math.max(1, Math.ceil(users.length / 20));
  const currentPage = Math.min(page, pageCount - 1);
  const printers = (data.printers || []).filter(p => !filters.printer_id || p.printer_id === filters.printer_id);
  const materials = (data.materials?.materials || []).filter(m => !filters.material_id || m.material_id === filters.material_id);
  const usage = data.usage;
  const jobsSeries = chartSeries(usage?.jobs_over_time || [], filters);
  const filamentSeries = chartSeries(data.materials?.filament_over_time || [], filters);
  const visibleKey: ReportKey = ({ Overview: "usage", Printers: "printers", Materials: "materials", Departments: "departments", Users: "users" } as const)[tab];
  const patchDraft = (key: keyof Filters, value: string) => setDraft(old => ({ ...old, [key]: value }));
  function apply(event: FormEvent) {
    event.preventDefault();
    const problem = showOtherDepartment && !draft.department.trim() ? "Enter a department name or select All departments." : filterError(draft);
    setFormError(problem);
    if (!problem) { setSnapshot({ data: {}, errors: {}, loading: true, updated: null }); setFilters({ ...draft }); setPage(0); }
  }
  function reset() {
    const next = recentFilters(); setDraft(next); setFilters(next); setFormError(null); setPage(0);
    setOtherDepartment(false);
    setSnapshot({ data: {}, errors: {}, loading: true, updated: null });
  }
  function download() {
    if (loading || !data[visibleKey]) return;
    let rows: (string | number | null)[][] = [];
    if (tab === "Overview" && usage) rows = [["Metric", "Value"], ...Object.entries(usage).filter(([, value]) => typeof value === "number").map(([key, value]) => [key, value as number]), [], ["Submission date (UTC)", "Jobs"], ...usage.jobs_over_time.map(p => [p.date, p.count]), [], ["Status", "Jobs"], ...usage.status_breakdown.map(s => [s.status, s.count])];
    if (tab === "Printers") rows = [["Printer ID", "Model", "Location", "Current status", "Jobs", "Completed", "Failed", "Hours (actual or estimated)", "Filament g (actual or estimated)", "Share of farm hours %", "Live queued/running jobs"], ...printers.map(p => [p.printer_id, p.model, p.location, p.status, p.total_jobs, p.completed_jobs, p.failed_jobs, p.total_print_hours, p.total_filament_g, p.utilization_pct, p.queue_length])];
    if (tab === "Materials") rows = [["Material", "Type", "Colour", "Jobs", "Filament g (actual or estimated)"], ...materials.map(m => [m.material_name, m.type, m.colour, m.total_jobs, m.total_filament_g]), [], ["Submission date (UTC)", "Filament g (rounded by API)"], ...(data.materials?.filament_over_time || []).map(p => [p.date, p.count])];
    if (tab === "Departments") rows = [["Job department", "Jobs", "Completed", "Failed", "Hours", "Filament g"], ...(data.departments || []).map(d => [d.department, d.total_jobs, d.completed_jobs, d.failed_jobs, d.total_print_hours, d.total_filament_g])];
    if (tab === "Users") rows = [["Name", "Email", "Student/staff number", "Profile department", "Role", "Jobs", "Completed", "Failed", "Hours", "Filament g"], ...users.map(u => [`${u.first_name} ${u.last_name}`, u.email, u.student_number, u.department, u.role, u.total_jobs, u.completed_jobs, u.failed_jobs, u.total_print_hours, u.total_filament_g])];
    const metadata: (string | number | null)[][] = [["UWA Print Farm usage report", tab], ["Updated UTC", updated?.toISOString() || ""], ["Date basis", "Submission date, UTC; actual values with estimate fallback"], ...Object.entries(filters).map(([key, value]) => [key, value || "All"]), ["User table search", tab === "Users" ? search : ""], []];
    const url = URL.createObjectURL(new Blob([csv([...metadata, ...rows])], { type: "text/csv;charset=utf-8;" }));
    const link = document.createElement("a"); link.href = url; link.download = `print-farm-${visibleKey}-${filters.from || "all"}-${filters.to || "time"}.csv`;
    document.body.append(link); link.click(); link.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <div className="usage-reports">
    <div className="report-heading"><div><span className="report-eyebrow">FARM INTELLIGENCE</span><h1>Usage & analytics</h1><p>Understand demand. Balance the farm. Plan your next print.</p></div><div className="report-actions"><button type="button" disabled={loading} onClick={() => { setSnapshot({ data: {}, errors: {}, loading: true, updated: null }); setRefresh(n => n + 1); }}><RefreshCw size={15} />Refresh</button><button type="button" className="report-primary" disabled={loading || !data[visibleKey]} onClick={download}><ArrowDownToLine size={15} />Export {tab.toLowerCase()}</button></div></div>
    <form className="report-filters" onSubmit={apply}>
      <div className="report-filter-title"><SlidersHorizontal size={17} /><b>Report filters</b><span>Submission dates · UTC</span></div>
      <div className="report-filter-grid">
        <label>From<input aria-label="From date UTC" type="date" value={draft.from} onChange={e => patchDraft("from", e.target.value)} /></label>
        <label>To<input aria-label="To date UTC" type="date" value={draft.to} onChange={e => patchDraft("to", e.target.value)} /></label>
        <label>Printer<select value={draft.printer_id} onChange={e => patchDraft("printer_id", e.target.value)}><option value="">All printers</option>{catalog.printers.map(p => <option value={p.printer_id} key={p.printer_id}>{printerName(p)}</option>)}</select></label>
        <label>Material<select value={draft.material_id} onChange={e => patchDraft("material_id", e.target.value)}><option value="">All materials</option>{catalog.materials.map(m => <option value={m.material_id} key={m.material_id}>{m.material_name} · {m.colour}</option>)}</select></label>
        <label>Job department<select value={showOtherDepartment ? "__other__" : draft.department} onChange={e => { const value = e.target.value; setOtherDepartment(value === "__other__"); patchDraft("department", value === "__other__" ? "" : value); }}><option value="">All departments</option>{departmentOptions.map(name => <option value={name} key={name}>{name}</option>)}<option value="__other__">Other department…</option></select></label>
        {showOtherDepartment && <label>Specify job department<input value={draft.department} onChange={e => patchDraft("department", e.target.value)} placeholder="Enter exact department name" required /></label>}
        <label>Job status<select value={draft.status} onChange={e => patchDraft("status", e.target.value)}><option value="">All statuses</option>{["pending_selection", "submitted", "queued", "printing", "completed", "ready_for_collection", "failed", "removed"].map(s => <option value={s} key={s}>{statusLabel(s)}</option>)}</select></label>
      </div>
      <div className="report-filter-footer"><div className="report-actions"><button type="button" onClick={() => setDraft({ ...draft, ...{ from: recentFilters(7).from, to: recentFilters(7).to } })}>Last 7 days</button><button type="button" onClick={() => setDraft({ ...draft, from: "", to: "" })}>All time</button><button type="button" onClick={reset}>Reset</button></div><button type="submit" className="report-primary">Apply filters</button></div>
      {draft.user_id && <p className="report-footnote">User filter: {draft.user_id} <button type="button" className="report-text-button" onClick={() => patchDraft("user_id", "")}>Clear user filter</button></p>}
      {formError && <p role="alert" className="report-error">{formError}</p>}
    </form>
    <div className="report-status" role="status"><span><Activity size={14} />{loading ? "Loading selected reports…" : updated ? `Updated ${updated.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" })}` : "Reports unavailable"}</span><span>{filters.from || "Beginning"} → {filters.to || "Latest"} · UTC{filters.printer_id && ` · ${catalog.printers.find(p => p.printer_id === filters.printer_id)?.model || "Selected printer"}`}{filters.material_id && ` · ${catalog.materials.find(m => m.material_id === filters.material_id)?.material_name || "Selected material"}`}{filters.department && ` · ${filters.department}`}{filters.status && ` · ${statusLabel(filters.status)}`}{filters.user_id && " · One user"}</span></div>
    {!loading && Object.keys(errors).length > 0 && <div className="report-error" role="alert">Some reports could not load: {Object.keys(errors).join(", ")}. Open that view for details, then try Refresh.</div>}
    <div className="report-tabs" role="group" aria-label="Report views">{tabs.map(t => <button type="button" aria-pressed={tab === t} className={tab === t ? "selected" : ""} key={t} onClick={() => setTab(t)}>{t}</button>)}</div>
    <ReportState loading={loading} error={errors[visibleKey]}>
      {tab === "Overview" && usage && <>
        <div className="report-kpis">{[
          ["Total jobs", number(usage.total_jobs, 0), `${number(usage.active_queued_jobs)} active or queued`],
          ["Completion share", usage.total_jobs ? `${number(usage.success_rate_pct)}%` : "—", `${number(usage.completed_jobs)} completed / all jobs`],
          ["Print hours", number(usage.total_print_hours), "Actual or estimated duration"],
          ["Filament · kg", number(usage.total_filament_g / 1000, 3), "Actual or estimated usage"],
        ].map(([label, value, note]) => <section className="report-kpi" key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></section>)}</div>
        <div className="report-summary"><span><b>{number(usage.failed_jobs)}</b> failed</span><span><b>{number(usage.cancelled_jobs)}</b> cancelled</span><span><b>{usage.total_jobs ? number(usage.avg_print_duration_min) : "—"}</b> average minutes / job</span></div>
        {usage.total_jobs === 0 && <p className="report-empty">No jobs match these filters. Try a wider date range or reset the filters.</p>}
        <div className="report-chart-grid"><ReportChart title="Jobs over time" note={`Jobs by submission date · ${jobsSeries.monthly ? "monthly" : "daily"} totals`} rows={jobsSeries.rows} kind="area" /><ReportChart title="Job status breakdown" note="Completed includes ready for collection. Active includes submitted, queued and printing." rows={usage.status_breakdown.map(s => ({ name: statusLabel(s.status), value: s.count }))} kind="donut" /></div>
      </>}
      {tab === "Printers" && data.printers && <>
        <div className="report-callout">Compare workload share with failures and the current queue before allocating more jobs. Queue values are a live snapshot, include printing jobs, and ignore date, material, department, user and status filters.</div>
        <div className="report-chart-grid"><ReportChart title="Share of farm print hours" note="Backend utilization_pct: printer hours ÷ filtered farm hours. This is not capacity utilization." unit="%" rows={printers.map(p => ({ name: printerName(p), value: p.utilization_pct }))} /><ReportChart title="Failure rate by printer" note="Failed ÷ all matching jobs. Printers without matching jobs are omitted." unit="%" rows={printers.filter(p => p.total_jobs > 0).map(p => ({ name: printerName(p), value: percent(p.failed_jobs, p.total_jobs)! }))} /><ReportChart title="Live queue & running jobs" note="Submitted + queued + printing, for each selected printer. Refresh to update." rows={printers.map(p => ({ name: printerName(p), value: p.queue_length }))} /></div>
        <div className="report-card report-table-scroll"><table><caption>Printer detail · filtered job metrics and current machine state</caption><thead><tr>{["Printer", "Current state", "Jobs", "Completed", "Failed", "Hours", "Filament g", "Live queue"].map(s => <th scope="col" key={s}>{s}</th>)}</tr></thead><tbody>{printers.map(p => <tr key={p.printer_id}><th scope="row">{printerName(p)}</th><td>{statusLabel(p.status)}</td><td>{p.total_jobs}</td><td>{p.completed_jobs}</td><td>{p.failed_jobs}</td><td>{number(p.total_print_hours)}</td><td>{number(p.total_filament_g)}</td><td>{p.queue_length}</td></tr>)}</tbody></table>{!printers.length && <p className="report-empty">No printers returned.</p>}</div>
      </>}
      {tab === "Materials" && data.materials && <><div className="report-chart-grid"><ReportChart title="Material consumption" note="Actual filament where available, otherwise the job estimate." unit="g" rows={materials.map(m => ({ name: `${m.material_name} · ${m.colour}`, value: m.total_filament_g }))} /><ReportChart title="Filament usage over time" note={`Grouped by job submission date, not consumption date · ${filamentSeries.monthly ? "monthly" : "daily"}. API rounds daily grams.`} unit="g" kind="area" rows={filamentSeries.rows} /></div><div className="report-card report-table-scroll"><table><caption>Material detail</caption><thead><tr>{["Material", "Type", "Colour", "Jobs", "Filament g"].map(s => <th scope="col" key={s}>{s}</th>)}</tr></thead><tbody>{materials.map(m => <tr key={m.material_id}><th scope="row">{m.material_name}</th><td>{m.type}</td><td>{m.colour}</td><td>{m.total_jobs}</td><td>{number(m.total_filament_g, 2)}</td></tr>)}</tbody></table>{!materials.length && <p className="report-empty">No materials returned.</p>}</div></>}
      {tab === "Departments" && data.departments && <><ReportChart title="Department demand" note="Print hours by the department recorded on the job. General includes jobs with no department." unit="hours" rows={data.departments.map(d => ({ name: d.department, value: d.total_print_hours }))} /><div className="report-card report-table-scroll"><table><caption>Department usage · actual values with estimate fallback</caption><thead><tr>{["Department", "Jobs", "Completed", "Failed", "Hours", "Filament g"].map(s => <th scope="col" key={s}>{s}</th>)}</tr></thead><tbody>{data.departments.map(d => <tr key={d.department}><th scope="row">{d.department}</th><td>{d.total_jobs}</td><td>{d.completed_jobs}</td><td>{d.failed_jobs}</td><td>{number(d.total_print_hours)}</td><td>{number(d.total_filament_g)}</td></tr>)}</tbody></table>{!data.departments.length && <p className="report-empty">No department usage for this selection.</p>}</div></>}
      {tab === "Users" && data.users && <section className="report-card"><div className="report-card-heading"><div><h2>User & student usage</h2><p>Search affects this table and its export. Department below is the user profile department; the filter above uses job department.</p></div></div><div className="report-user-controls"><label>Search users<input type="search" placeholder="Name, email, student number…" value={search} onChange={e => { setSearch(e.target.value); setPage(0); }} /></label><label>Sort by<select value={sort} onChange={e => { setSort(e.target.value); setPage(0); }}><option value="jobs">Most jobs</option><option value="hours">Most hours</option><option value="filament">Most filament</option><option value="name">Name A–Z</option></select></label></div><div className="report-table-scroll"><table><caption>{users.length} matching users · export includes all matching pages</caption><thead><tr>{["User", "Number / department", "Role", "Jobs", "Completed", "Failed", "Hours", "Filament g", "Explore"].map(s => <th scope="col" key={s}>{s}</th>)}</tr></thead><tbody>{users.slice(currentPage * 20, currentPage * 20 + 20).map(u => <tr key={u.user_id}><th scope="row">{u.first_name} {u.last_name}<small>{u.email}</small></th><td>{u.student_number || "—"}<small>{u.department || "Unspecified"}</small></td><td>{statusLabel(u.role)}</td><td>{u.total_jobs}</td><td>{u.completed_jobs}</td><td>{u.failed_jobs}</td><td>{number(u.total_print_hours)}</td><td>{number(u.total_filament_g)}</td><td><button type="button" className="report-text-button" onClick={() => { const next = { ...filters, user_id: u.user_id }; setDraft(next); setFilters(next); setTab("Overview"); setSnapshot({ data: {}, errors: {}, loading: true, updated: null }); }}>View usage</button></td></tr>)}</tbody></table>{!users.length && <p className="report-empty">No users match this selection.</p>}</div><div className="report-pagination"><button type="button" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous</button><span>Page {currentPage + 1} of {pageCount}</span><button type="button" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}>Next</button></div></section>}
    </ReportState>
    <details className="report-definitions"><summary>How these metrics are calculated</summary><ul><li>Dates filter job submission timestamps in UTC, not completion timestamps.</li><li>Completion share is completed plus ready-for-collection jobs divided by all matching jobs, including queued, failed and cancelled jobs.</li><li>Hours and filament use actual values when the backend has them, otherwise estimates. They include all selected job statuses and are not audited consumption totals.</li><li>Printer workload share is not uptime or available-capacity utilization. Some jobs may not yet have a printer or material assigned.</li><li>Live queue counts ignore report filters except the selected printer and include running jobs. They update when you refresh.</li><li>Department filtering requires an exact job department. The backend’s General group also includes missing departments; typing General only matches literal General values.</li><li>No revenue, payment totals or remaining stock are returned by these endpoints, so those figures are not inferred here.</li></ul></details>
  </div>;
}
