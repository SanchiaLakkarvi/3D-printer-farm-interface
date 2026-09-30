/** Optional browser checks. Start the app with NEXT_PUBLIC_API_BASE_URL=http://localhost:8000.
 * All API responses here are explicit test fixtures intercepted in Playwright;
 * no fixture values or test accounts are added to the production application.
 * Run: node tests/reports-browser.mjs (requires Playwright + Chromium installed).
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
const { chromium } = createRequire(import.meta.url)("playwright");
const browser = await chromium.launch({ headless: true, ...(process.env.REPORTS_CHROMIUM_PATH ? { executablePath: process.env.REPORTS_CHROMIUM_PATH } : {}) });
const context = await browser.newContext({ viewport: { width: 1440, height: 1150 } });
const page = await context.newPage();
const errors = [];
page.on("pageerror", error => errors.push(error.message));
await context.addInitScript(() => sessionStorage.setItem("access_token", "browser-fixture-only"));
let mode = "normal", role = "admin";
let requests = [];
const totals = { total_jobs: 12, completed_jobs: 8, failed_jobs: 1, total_print_hours: 32.5, total_filament_g: 860 };
const printers = [{ ...totals, printer_id: "11111111-1111-4111-8111-111111111111", model: "Prusa CORE One", location: "Perkins", status: "printing", utilization_pct: 60, queue_length: 3 }, { ...totals, printer_id: "22222222-2222-4222-8222-222222222222", model: "Prusa XL", location: "Perkins", status: "idle", utilization_pct: 40, queue_length: 1 }];
const materials = { materials: [{ material_id: "33333333-3333-4333-8333-333333333333", material_name: "PLA Black", type: "PLA", colour: "Black", total_jobs: 12, total_filament_g: 860 }], filament_over_time: [{ date: "2026-09-01", count: 200 }, { date: "2026-09-03", count: 660 }] };
const usage = { ...totals, cancelled_jobs: 1, active_queued_jobs: 2, success_rate_pct: 66.7, avg_print_duration_min: 162.5, jobs_over_time: [{ date: "2026-09-01", count: 3 }, { date: "2026-09-03", count: 9 }], status_breakdown: [{ status: "completed", count: 8 }, { status: "failed", count: 1 }, { status: "cancelled", count: 1 }, { status: "active", count: 2 }] };
const users = Array.from({ length: 24 }, (_, i) => ({ ...totals, user_id: `10000000-0000-4000-8000-${String(i).padStart(12, "0")}`, first_name: "Test", last_name: `User ${i}`, email: `user${i}@example.test`, student_number: `${22000000+i}`, department: "Engineering", role: "student" }));
const departments = [{ ...totals, department: "Engineering" }];
await page.route("http://localhost:8000/**", async route => {
  const url = new URL(route.request().url());
  if (url.pathname === "/api/auth/me") return route.fulfill({ json: { id: "fixture", email: "admin@example.test", first_name: "Test", last_name: "Admin", role, department: null, student_number: null } });
  if (!url.pathname.includes("/reports/")) return route.fulfill({ json: [] });
  requests.push(url);
  const key = url.pathname.split("/").at(-1);
  if (mode === "denied") return route.fulfill({ status: 403, json: { detail: "Forbidden" } });
  if (mode === "partial" && key === "materials") return route.fulfill({ status: 500, json: {} });
  if (mode === "old") await new Promise(resolve => setTimeout(resolve, 500));
  const emptyUsage = { total_jobs: 0, completed_jobs: 0, failed_jobs: 0, total_print_hours: 0, total_filament_g: 0, cancelled_jobs: 0, active_queued_jobs: 0, success_rate_pct: 0, avg_print_duration_min: 0, jobs_over_time: [], status_breakdown: [] };
  const data = mode === "empty" ? { usage: emptyUsage, printers: [], materials: { materials: [], filament_over_time: [] }, users: [], departments: [] } : { usage: mode === "old" ? { ...usage, total_jobs: 999 } : usage, printers, materials, users, departments };
  await route.fulfill({ json: data[key] }).catch(() => {});
});
const button = name => page.getByRole("button", { name, exact: true });
async function ready() { await button("Refresh").waitFor(); await page.waitForFunction(() => [...document.querySelectorAll('button')].find(b => b.textContent === 'Refresh' && !b.disabled)); }
try {
  await page.goto(process.env.REPORTS_TEST_URL || "http://127.0.0.1:5173");
  await button("Usage reports").click(); await ready();
  // Fix dates so screenshots stay reproducible on a later day.
  await page.getByLabel("From date UTC").fill("2026-09-01"); await page.getByLabel("To date UTC").fill("2026-09-27");
  await button("Apply filters").click(); await ready();
  assert.equal(await page.locator('.report-kpi strong').first().innerText(), "12");
  assert.equal(await page.locator('.report-chart svg.recharts-surface').count(), 2);
  await mkdir("/tmp/reports-browser", { recursive: true });
  await page.screenshot({ path: "/tmp/reports-browser/overview-desktop.png", fullPage: true });
  await button("Printers").click(); assert.equal(await page.locator('.report-chart svg.recharts-surface').count(), 3);
  await page.screenshot({ path: "/tmp/reports-browser/printers-desktop.png", fullPage: true });
  await button("Materials").click(); assert.equal(await page.locator('.report-chart svg.recharts-surface').count(), 2);
  await button("Departments").click(); assert.equal(await page.locator('.report-chart svg.recharts-surface').count(), 1);
  await button("Users").click(); assert.equal(await page.locator('tbody tr').count(), 20);
  await button("Next").click(); assert.equal(await page.locator('tbody tr').count(), 4);
  await page.getByLabel("Search users").fill("user23@example.test"); assert.equal(await page.locator('tbody tr').count(), 1);
  const downloading = page.waitForEvent("download"); await button("Export users").click(); const download = await downloading;
  const { readFile } = await import("node:fs/promises"); const exported = await readFile(await download.path(), "utf8");
  assert.match(exported, /user23@example.test/); assert.doesNotMatch(exported, /user22@example.test/);
  await button("View usage").click(); await ready(); assert.match(requests.at(-1).search, /user_id=/);
  await button("Reset").click(); await ready();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "/tmp/reports-browser/overview-mobile.png", fullPage: true });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), "mobile must not overflow horizontally");
  await page.setViewportSize({ width: 1440, height: 1150 });
  mode = "partial"; await button("Refresh").click(); await ready(); await button("Materials").click(); assert.match(await page.locator('.usage-reports').innerText(), /HTTP 500/);
  await button("Overview").click(); assert.equal(await page.locator('.report-kpi strong').first().innerText(), "12");
  mode = "empty"; await button("Refresh").click(); await ready(); assert.equal(await page.locator('.report-kpi strong').nth(1).innerText(), "—");
  assert.match(await page.locator('.usage-reports').innerText(), /No jobs match/);
  mode = "denied"; await button("Refresh").click(); await ready(); assert.equal(await page.locator('.report-kpi').count(), 0); assert.equal(await button("Export overview").isDisabled(), true);
  role = "student"; mode = "normal"; await page.reload(); await page.getByText("Student account", { exact: true }).waitFor(); assert.equal(await button("Usage reports").count(), 0);
  role = "farmer"; await page.reload(); await button("Usage reports").click(); await ready(); assert.equal(await page.locator('.report-kpi').count(), 4);
  assert.deepEqual(errors, []);
  console.log("PASS: eight charts, desktop/mobile, pagination, search, CSV, user drill-down, partial error, empty data, 403, Student/Farmer navigation; no browser exceptions.");
} finally { await browser.close(); }
