"use client";
import { useId, useState, type ReactNode } from "react";
import { ResponsiveContainer, CartesianGrid, XAxis, YAxis, Tooltip, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell } from "recharts";
import { number } from "@/lib/reports/model";

export type ChartRow = { name: string; value: number };
const colours = ["#167db0", "#159574", "#d29022", "#ce5366", "#7764b5", "#697d91"];
const statusColours: Record<string, string> = { Completed: "#159574", Active: "#167db0", Failed: "#ce5366", Cancelled: "#697d91" };

/** Every chart has a text/table alternative; values never depend on colour alone. */
export function ReportChart({ title, note, rows, kind = "bar", unit = "jobs" }: {
  title: string; note: string; rows: ChartRow[]; kind?: "bar" | "area" | "donut"; unit?: string;
}) {
  const id = useId().replaceAll(":", "");
  const [table, setTable] = useState(false);
  // Categorical charts show the top ten for legibility. The table keeps every row.
  const visible = kind === "bar" ? [...rows].sort((a, b) => b.value - a.value).slice(0, 10) : rows;
  const hasValues = rows.some(row => row.value > 0);
  return <section className="report-card" aria-labelledby={`${id}-title`}>
    <div className="report-card-heading"><div><h2 id={`${id}-title`}>{title}</h2><p>{note}</p></div>
      <button type="button" className="report-text-button" aria-expanded={table} onClick={() => setTable(!table)}>{table ? "Show chart" : "View data"}</button></div>
    {table ? <div className="report-table-scroll"><table><caption>{title} · {unit}</caption><thead><tr><th scope="col">Category / date</th><th scope="col">{unit}</th></tr></thead><tbody>{rows.map((r, i) => <tr key={`${r.name}-${i}`}><th scope="row">{r.name}</th><td>{number(r.value, 2)}</td></tr>)}</tbody></table>{!rows.length && <p className="report-empty">No matching data.</p>}</div>
      : !hasValues ? <div className="report-empty-chart">No values to chart for this selection.</div> : <>
      <div className="report-chart" role="group" aria-label={`${title}. ${rows.length} categories. Use View data for exact values.`}>
        <ResponsiveContainer width="100%" height="100%">
          {kind === "area" ? <AreaChart data={visible} margin={{ top: 12, right: 20, bottom: 10, left: 0 }} accessibilityLayer>
            <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#167db0" stopOpacity={0.22} /><stop offset="100%" stopColor="#167db0" stopOpacity={0.02} /></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e4ebef" /><XAxis dataKey="name" tick={{ fontSize: 11 }} minTickGap={40} tickLine={false} axisLine={false} /><YAxis tick={{ fontSize: 11 }} width={52} tickLine={false} axisLine={false} allowDecimals={unit !== "jobs"} />
            <Tooltip formatter={(v) => [number(Number(v), 2), unit]} /><Area type="linear" dataKey="value" stroke="#167db0" strokeWidth={2.5} fill={`url(#${id})`} isAnimationActive={false} dot={visible.length === 1} />
          </AreaChart> : kind === "donut" ? <PieChart accessibilityLayer><Tooltip formatter={(v) => [number(Number(v)), unit]} /><Pie data={visible} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="85%" paddingAngle={2} isAnimationActive={false}>{visible.map((r, i) => <Cell key={r.name} fill={statusColours[r.name] || colours[i % colours.length]} />)}</Pie></PieChart>
          : <BarChart data={visible} layout="vertical" margin={{ top: 6, right: 25, bottom: 8, left: 4 }} accessibilityLayer><CartesianGrid strokeDasharray="3 5" horizontal={false} stroke="#e4ebef" /><XAxis type="number" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={unit !== "jobs"} /><YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(s: string) => s.length > 22 ? s.slice(0, 21) + "…" : s} /><Tooltip formatter={(v) => [number(Number(v), 2), unit]} /><Bar dataKey="value" fill="#167db0" radius={[0, 5, 5, 0]} maxBarSize={24} isAnimationActive={false} /></BarChart>}
        </ResponsiveContainer>
      </div>
      {kind === "donut" && <div className="report-legend">{visible.map((r, i) => <span key={r.name}><i style={{ background: statusColours[r.name] || colours[i % colours.length] }} />{r.name}<b>{number(r.value)}</b></span>)}</div>}
      {kind === "bar" && rows.length > 10 && <p className="report-footnote">Top 10 shown. View data includes all {rows.length} categories.</p>}
    </>}
  </section>;
}

export function ReportState({ loading, error, children }: { loading: boolean; error?: string; children: ReactNode }) {
  if (loading) return <div className="report-card report-placeholder" role="status">Loading report…</div>;
  if (error) return <div className="report-error" role="alert">{error}</div>;
  return <>{children}</>;
}
