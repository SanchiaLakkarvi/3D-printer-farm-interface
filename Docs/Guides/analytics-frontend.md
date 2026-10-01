# Usage reporting frontend for PR #115

Adds a real-data dashboard to the Farmer and Admin **Usage reports** menu.
Backend dependency: PR #115, reviewed at `ede2506c01af8f64b3cc895921395c6944463968`.
The five endpoints are already in that PR; this frontend does not modify backend data.

## What changed

- Eight charts: job submission trend, status donut, printer workload share, printer failure rate, live queue/running jobs, material consumption, filament trend, department hours.
- KPI cards, exact department/status/printer/material/date filters, user drill-down.
- Searchable/sortable user table with 20-row pages and full matching export.
- CSV exports for each view with applied-filter metadata, proper quoting and formula neutralisation.
- Explicit empty states, errors, runtime response validation, request cancellation, timeout and manual refresh.
- Large time ranges become monthly charts; categorical charts display top ten with all rows available in View data.
- Lazy loading avoids putting Recharts into the initial login/student bundle.
- Labels, keyboard focus, table alternatives, responsive layout and reduced-motion treatment.

## Files to understand

| File under frontend/UWA-3D-Print-Farm | Purpose |
| --- | --- |
| app/page.tsx | Add Farmer navigation and lazy dashboard integration |
| lib/reports/model.ts | Runtime contracts, filter/date logic, chart aggregation and CSV |
| lib/reports/client.ts | Existing bearer token, fetch, abort, HTTP/schema error handling |
| components/reports/usage-reports.tsx | Filters, parallel loading, five views, exports, user drill-down |
| components/reports/report-charts.tsx | Shared charts with complete data-table alternatives |
| components/reports/reports.css | Scoped responsive styling |
| tests/reports.test.mjs | 16 reporting unit/contract tests |
| tests/reports-browser.mjs | Optional browser fixture checks; no production sample data |
| tsconfig.reports.json | Type-check this feature and its page integration |

## Metric definitions and backend limitations

1. Date boundaries and series use UTC submission dates. The inclusive end boundary is `23:59:59.999999Z`, matching backend microsecond precision.
2. `success_rate_pct` means completed/ready-for-collection jobs divided by all matching jobs. The UI calls it **Completion share** because queued jobs are also in the denominator.
3. Duration and filament use actual values with estimated-value fallback, including non-completed jobs. The existing backend uses Python `or`, so even an actual zero falls back to an estimate. Accurate consumed-only reporting requires backend changes.
4. `utilization_pct` is share of filtered farm hours, not printer uptime or available-capacity utilization. The label reflects this.
5. `queue_length` includes submitted, queued and printing jobs; it ignores date/material/department/user/status filters. The UI filters displayed printers but preserves the current snapshot values.
6. Material time-series values are rounded to whole grams by the backend and grouped by submission date. Rounded series may differ slightly from totals.
7. Job departments drive filtering and department totals; user rows show profile departments. Backend `General` combines missing departments and literal General values. Filtering by General only matches the literal value; no synthetic null-department filter is sent.
8. Jobs without an assigned printer/material can appear in totals but not in per-device/material charts.
9. The PR provides no payment, revenue, remaining-filament, downtime or capacity data. The UI does not fabricate those metrics.
10. All five reports load concurrently on Apply/Refresh. There is no aggressive polling. The backend currently aggregates entire matching job sets and returns all user rows; client pagination cannot remove that server-side scaling limit. Large farms will eventually need SQL aggregation and server pagination.

## Run and verify

From the frontend folder, with Node >=22.13:

```bash
npm ci
npx tsc --project tsconfig.reports.json --noEmit
npx eslint components/reports lib/reports tests/reports.test.mjs tests/reports-browser.mjs
node --test tests/reports.test.mjs
npx vinext build
```

`npx vinext build` bypasses the repository's GNU-timeout wrapper, which is inconvenient on macOS. It builds the same application.
The repository-wide `npx tsc --noEmit` currently reports missing Cloudflare `cloudflare:workers`, `Fetcher`, and `D1Database` types outside this feature. `tsconfig.reports.json` checks the new feature, page, and their imports; it does not fix or hide those repository-wide errors.

Use an existing Farmer/Admin account with the real backend. Selecting the role on the login page does not grant access. The API remains responsible for authorization. A Student account must not see Usage reports.

### Optional automated browser check

Start the app in one terminal:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev -- --host 127.0.0.1
```

In a second terminal in the frontend folder:

```bash
npm install --no-save --package-lock=false playwright
npx playwright install chromium
node tests/reports-browser.mjs
```

This intercepts API calls with fixture responses and writes screenshots to `/tmp/reports-browser`. It does not prove live database integration. A local production backend is not required for this fixture test.

### Real-backend acceptance checklist

- Run the backend from PR #115 and sign in as an authorised Farmer/Admin.
- Open Usage reports; compare totals against `/api/reports/usage` in browser Network.
- Change dates, printer, material, department and status; Apply. Check requests include those values.
- Confirm the end date includes jobs late in that UTC day.
- Open all five views; test View data, user search/sort/pages, View usage and clear-user filtering.
- Export every view; user export must contain all matching pages and no hidden unmatched users.
- Try an empty range; zero jobs should show no-data messages, with completion share shown as a dash.
- Stop the backend; Refresh must report an error, not plausible zero metrics.
- Rapidly apply two filter selections; the newest selection must win.
- Sign out and back in as Student; reports must not be available.
- Inspect desktop and narrow mobile layouts and keyboard navigation.

## Suggested PR description

The backend in #115 exposes reporting data, but the portal's Usage reports screen is a placeholder. This change gives Farmer/Admin users a filtered reporting dashboard with eight charts, metric definitions, usage tables and CSV exports. It uses existing authentication and explicitly distinguishes historical job metrics from the live queue snapshot.

Frontend only; depends on #115. Review the diff against `feat/admin-usage-reporting` while that PR is open. After it merges, retarget/rebase against main as appropriate.

## GenAI disclosure

This implementation was generated with ChatGPT assistance after inspection of PR #115 and the existing frontend. Review the code and tests, verify it against the team's real backend, and describe your own integration, testing and modifications accurately in the contribution report.
