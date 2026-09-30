import assert from "node:assert/strict";
import test, { after, beforeEach } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

// Use the same TS/alias loading approach as the project's auth tests.
const root = fileURLToPath(new URL("..", import.meta.url));
const vite = await createServer({ appType: "custom", configFile: false, root,
  resolve: { alias: { "@": root } }, server: { middlewareMode: true } });
const model = await vite.ssrLoadModule("/lib/reports/model.ts");
const client = await vite.ssrLoadModule("/lib/reports/client.ts");
const originalFetch = globalThis.fetch;
after(async () => { globalThis.fetch = originalFetch; delete globalThis.sessionStorage; await vite.close(); });
beforeEach(() => {
  globalThis.sessionStorage = { getItem: () => "test-token" };
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
});
const blank = model.blankFilters;
const signal = () => new AbortController().signal;

test("inclusive end date preserves all microseconds and encodes exact department", () => {
  const query = new URLSearchParams(model.reportQuery({ ...blank, from: "2026-09-01", to: "2026-09-27", department: "Mechanical & Electrical", status: "removed" }));
  assert.equal(query.get("from_date"), "2026-09-01T00:00:00Z");
  assert.equal(query.get("to_date"), "2026-09-27T23:59:59.999999Z");
  assert.equal(query.get("department"), "Mechanical & Electrical");
  assert.equal(query.get("status"), "removed");
  assert.equal(query.has("user_id"), false);
});
test("invalid, impossible and reversed dates are rejected", () => {
  for (const f of [{ from: "2026-02-30" }, { from: "bad" }, { from: "2026-09-28", to: "2026-09-27" }]) assert.throws(() => model.reportQuery({ ...blank, ...f }));
  assert.equal(model.filterError({ ...blank, from: "2024-02-29" }), null);
});
test("default range includes exactly thirty UTC dates across month boundaries", () => {
  const f = model.recentFilters(30, new Date("2026-03-01T23:00:00Z"));
  assert.equal(f.from, "2026-01-31"); assert.equal(f.to, "2026-03-01");
});
test("daily chart fills missing days without changing totals", () => {
  const result = model.chartSeries([{ date: "2026-09-03", count: 2 }, { date: "2026-09-01", count: 4 }], { ...blank, from: "2026-09-01", to: "2026-09-04" });
  assert.deepEqual(result.rows.map(r => r.value), [4, 0, 2, 0]);
  assert.equal(result.monthly, false);
});
test("long ranges aggregate by month and preserve total", () => {
  const result = model.chartSeries([{ date: "2026-01-01", count: 4 }, { date: "2026-01-03", count: 2 }, { date: "2026-12-01", count: 7 }], blank);
  assert.equal(result.monthly, true); assert.equal(result.rows.length, 12);
  assert.equal(result.rows[0].value, 6); assert.equal(result.rows.reduce((n, r) => n + r.value, 0), 13);
});
test("zero denominator has no invented success or failure percentage", () => {
  assert.equal(model.percent(0, 0), null); assert.equal(model.percent(1, 4), 25);
});
test("CSV quotes commas, quotes and newlines, and prevents formula execution", () => {
  const result = model.csv([["a,b", 'a"b', "a\nb", " =SUM(1,2)", "@SUM(1)", 2]]);
  assert.equal(result, '\uFEFF"a,b","a""b","a\nb","\' =SUM(1,2)","\'@SUM(1)","2"');
});
test("missing login token blocks the request before network access", async () => {
  globalThis.sessionStorage = { getItem: () => null };
  globalThis.fetch = () => { throw new Error("must not fetch"); };
  await assert.rejects(client.fetchReport("users", blank, signal()), e => e.status === 401);
});
test("report request uses existing auth token, filters and cancellation signal", async () => {
  const controller = new AbortController();
  globalThis.fetch = async (url, init) => {
    assert.equal(init.headers.Authorization, "Bearer test-token");
    assert.equal(init.signal, controller.signal); assert.equal(init.cache, "no-store");
    assert.match(url, /\/api\/reports\/users\?user_id=user-123/);
    return Response.json([]);
  };
  assert.deepEqual(await client.fetchReport("users", { ...blank, user_id: "user-123" }, controller.signal), []);
});
for (const status of [401, 403, 404, 422, 500]) test(`HTTP ${status} produces a clear error, never an empty report`, async () => {
  globalThis.fetch = async () => new Response("failure", { status });
  await assert.rejects(client.fetchReport("users", blank, signal()), e => e.status === status);
});
test("malformed numeric values and invalid series dates fail validation", async () => {
  globalThis.fetch = async () => Response.json([{ department: "Engineering", total_jobs: "2" }]);
  await assert.rejects(client.fetchReport("departments", blank, signal()), /unexpected report format/);
  assert.equal(model.schemas.materials.safeParse({ materials: [], filament_over_time: [{ date: "2026-99-99", count: 3 }] }).success, false);
});
test("network failure and cancellation are distinct", async () => {
  globalThis.fetch = async () => { throw new TypeError("offline"); };
  await assert.rejects(client.fetchReport("users", blank, signal()), /Cannot reach/);
  const controller = new AbortController(); controller.abort();
  const abort = new DOMException("Aborted", "AbortError");
  globalThis.fetch = async () => { throw abort; };
  await assert.rejects(client.fetchReport("users", blank, controller.signal), e => e === abort);
});
