"use client";

import { AlertTriangle, CheckCircle2, Upload } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { api, ApiError, type GcodeValidation, type JobSubmission, type Material } from "@/lib/api/client";
import { formatCost, formatDuration, formatWhen, PRINTER_LABELS, printerAcceptsJobs } from "@/lib/api/format";

type Props = { role: "student" | "farmer" | "admin"; openJobs: () => void };

const STAGE_LABELS: Record<string, string> = {
  FILE_FORMAT_VALIDATION: "File format",
  PARSE_AND_INTEGRITY: "File integrity",
  READ_METADATA: "Slicer settings",
  M862_EXECUTABLE_CROSS_CHECK: "Printer commands",
  CHECK_BOTH_PRINTERS: "Printer compatibility",
  SUPPORTED_PRINTER_MATCH: "Supported printer match",
};

export function LiveUpload({ role, openJobs }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<GcodeValidation | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [printerId, setPrinterId] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<JobSubmission | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.materials().then(setMaterials).catch(() => setMaterials([]));
  }, []);

  const required = result?.required_material?.toUpperCase() ?? null;
  const matching = materials.filter((m) => m.type.toUpperCase() === required);
  const usablePrinters = (result?.compatible_printers ?? []).filter((p) => printerAcceptsJobs(p.status));

  async function choose(e: ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0];
    e.target.value = "";
    if (!picked) return;
    setResult(null);
    setSubmitted(null);
    setError("");
    setPrinterId("");
    setMaterialId("");
    if (!/\.gcode$/i.test(picked.name) && !/\.bgcode$/i.test(picked.name)) {
      setFile(null);
      setError("Please choose a .gcode or .bgcode file.");
      return;
    }
    setFile(picked);
    setChecking(true);
    try {
      const checked = await api.validate(picked);
      setResult(checked);
      const first = checked.compatible_printers.find((p) => printerAcceptsJobs(p.status));
      if (first) setPrinterId(first.printer_id);
      const only = materials.filter((m) => m.type.toUpperCase() === checked.required_material?.toUpperCase());
      if (only.length === 1) setMaterialId(only[0].id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Validation failed.");
    } finally {
      setChecking(false);
    }
  }

  async function submit() {
    if (!file || !printerId || !materialId) return;
    setSubmitting(true);
    setError("");
    try {
      setSubmitted(await api.submit(file, printerId, materialId));
    } catch (err) {
      const detail = err instanceof ApiError ? [err.message, ...err.details].join(" ") : "Could not submit the job.";
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  }

  function reset() {
    setFile(null);
    setResult(null);
    setSubmitted(null);
    setError("");
  }

  return (
    <>
      <div className="heading">
        <div>
          <span>{role === "student" ? "Student" : role === "farmer" ? "Printer Farmer" : "Administrator"} portal</span>
          <h1>Upload file</h1>
          <p>Upload a pre-sliced G-code file. It is checked against the farm’s printers before you can submit it to the queue.</p>
        </div>
        <button onClick={() => input.current?.click()}><Upload />Choose G-code file</button>
      </div>

      <section className="upload-panel">
        <input ref={input} className="file-input" type="file" accept=".gcode,.bgcode" onChange={choose} />
        <button className="drop-zone" onClick={() => input.current?.click()} disabled={checking || submitting}>
          <i><Upload /></i>
          <b>{file?.name ?? "Choose a G-code file"}</b>
          <small>{checking ? "Checking your file…" : ".gcode and .bgcode files are accepted"}</small>
        </button>
        {error && <div className="error">{error}</div>}

        {result && !result.passed && (
          <section className="panel farm-result">
            <h2><AlertTriangle /> This file can’t be printed</h2>
            <p>{result.message}</p>
            {result.errors.map((e) => <div className="error" key={e}>{e}</div>)}
            <ul className="farm-stages">
              {result.stages.map((s) => <li key={s.stage} className={s.status === "PASS" ? "ok" : "bad"}>{s.status === "PASS" ? "✓" : "✕"} {STAGE_LABELS[s.name] ?? s.name}</li>)}
            </ul>
            <p className="farm-hint">Re-slice the model in PrusaSlicer with the UWA-approved printer profile and upload it again.</p>
          </section>
        )}

        {result?.passed && !submitted && (
          <div className="summary-grid">
            <section className="panel summary">
              <span>PRINT JOB SUMMARY</span>
              <h2><CheckCircle2 /> File checked</h2>
              <dl>
                <div><dt>File</dt><dd>{result.filename}</dd></div>
                <div><dt>Material in file</dt><dd>{result.required_material ?? "—"}</dd></div>
                <div><dt>Estimated time</dt><dd>{formatDuration(result.est_duration_min)}</dd></div>
                <div><dt>Estimated filament</dt><dd>{result.est_filament_g != null ? `${result.est_filament_g} g` : "—"}</dd></div>
                <div className="total"><dt>Estimated cost</dt><dd>{formatCost(result.estimated_cost_usd)}</dd></div>
              </dl>
            </section>
            <section className="panel farm-choose">
              <h2>Choose where to print</h2>
              <label>Printer
                <select value={printerId} onChange={(e) => setPrinterId(e.target.value)}>
                  <option value="">Select a printer…</option>
                  {result.compatible_printers.map((p) => (
                    <option key={p.printer_id} value={p.printer_id} disabled={!printerAcceptsJobs(p.status)}>
                      {p.model}{p.location ? ` — ${p.location}` : ""} ({PRINTER_LABELS[p.status]})
                    </option>
                  ))}
                </select>
              </label>
              {result.compatible_printers.length === 0 && <div className="error">No printer in the farm is set up for this file’s slicer profile.</div>}
              {result.compatible_printers.length > 0 && usablePrinters.length === 0 && <div className="error">Compatible printers are currently unavailable.</div>}
              <label>Material
                <select value={materialId} onChange={(e) => setMaterialId(e.target.value)}>
                  <option value="">Select {required ?? "a"} filament…</option>
                  {matching.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.colour})</option>)}
                </select>
              </label>
              {matching.length === 0 && <div className="error">No {required} filament is set up yet. Ask a farmer or admin to add it.</div>}
              <button className="primary" disabled={!printerId || !materialId || submitting} onClick={submit}>{submitting ? "Submitting…" : "Submit to print queue"}</button>
              <p className="farm-hint">Pricing: $2.00 for the first hour, $0.50 for each additional hour. Payment is not taken online yet.</p>
            </section>
          </div>
        )}

        {submitted && (
          <section className="panel farm-result">
            <h2><CheckCircle2 /> Added to the queue</h2>
            <p>{submitted.filename} will start around <b>{formatWhen(submitted.est_start_time)}</b> and finish around <b>{formatWhen(submitted.est_completion_time)}</b>. Estimated cost {formatCost(submitted.estimated_cost_usd)}.</p>
            <div className="farm-actions">
              <button className="primary" onClick={openJobs}>View my jobs</button>
              <button className="farm-secondary" onClick={reset}>Upload another file</button>
            </div>
          </section>
        )}
      </section>
    </>
  );
}
