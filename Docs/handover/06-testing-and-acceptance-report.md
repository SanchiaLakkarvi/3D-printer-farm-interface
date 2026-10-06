# Testing and Acceptance Report

**Group 16 — UWA 3D Printer Farm Interface**

| Document control | Value |
| --- | --- |
| Document version | 1.2 |
| Evidence review date | 6 October 2026 |
| Implementation baseline | `019cc9945961afd3ef90e3568c7a1409b7b995a8` |
| Automated execution for this baseline | Not independently verified from the evidence retrieved |
| Client approval | Christopher Lamb approved Group 16's MVP in writing on 11 August 2026. See Section 10. |

## 1. Release assessment

The repository contains automated tests for backend services, authentication, validation, printer interactions and frontend clients. Earlier pull requests report successful checks for their respective changes. Those reports are historical contributor statements, not independently verified execution results for the implementation baseline recorded above.

| Evidence | Recorded result or observation | Qualification |
| --- | --- | --- |
| Backend reporting PR #115 | Contributor reports 10 reporting tests passed and a full suite of 145 passed, 1 skipped and 0 failures. | Applies to the PR's reported testing context; not a final-release rerun. |
| Frontend reporting PR #130 | Contributor reports 16 report tests passed, a scoped TypeScript check passed, a frontend build passed and a local check using live report data. | Applies to the PR's reported testing context; execution logs were not retrieved during this evidence review. |
| GitHub workflow/status lookup for the recorded baseline | No workflow runs or combined-status entries were returned. | No automated CI result was retrieved for this commit through these lookups. |
| Local screenshots in Documents 01–04 | Selected interface views, validation results, mock-printer states and a displayed chatbot response are documented. | Each image supports its visible state; it does not establish comprehensive end-to-end acceptance. |
| Final baseline automated test totals | Not independently verified. | Fresh execution records are required before reporting final pass/fail totals. |

Historical evidence:

- [PR #115 — Backend reporting](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/pull/115)
- [PR #130 — Frontend reporting](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/pull/130)

Client approval of Group 16's MVP is recorded in the email dated 11 August 2026. That approval relates to the MVP discussed at that stage. Final automated results for the October implementation baseline are not independently verified by the evidence retrieved. Physical-printer commissioning requires separate evidence.

## 2. Scope and evidence labels

This report distinguishes repository test source, historical contributor reports, local screenshots and client approval. No new automated test execution is claimed by this evidence review.

| Label | Meaning |
| --- | --- |
| Source evidence | Repository files show the available test implementation and fixture configuration. Their presence does not establish a passing result. |
| Historical reported result | A contributor reports checks in a linked pull request. The result applies to that change's reported testing context. |
| Screenshot observation | A supplied capture records a visible interface state or response. It does not establish every related action or integration. |
| Client approval | Written approval of the MVP discussed with the client on 11 August 2026. |
| Outstanding verification | A check whose final-release execution evidence is not established in this report. |

No final-release coverage percentage, complete suite pass or physical-printer acceptance is claimed.

## 3. Test environment and limitations

The complete execution environment for the historical PR results is not established by the evidence retrieved.

The reviewed backend fixtures use Fake Auth and an in-memory SQLite database. They replace PostgreSQL JSONB columns with JSON and remove server defaults for fixture compatibility. Their results cannot establish PostgreSQL migration or production transaction behaviour.

The reviewed frontend reporting tests substitute fetch responses and session storage. The mock PrusaLink facade tests use a stub worker. These checks do not establish live-provider, browser-to-backend or physical-printer integration.

A fresh execution record should include the commit SHA, local changes, date, environment, dependency versions, command, exit code, complete output and any exclusions.

## 4. Verification commands — execution evidence to be recorded

These commands identify checks to run after installing the documented dependencies in an isolated test environment. No result is assigned until output is retained.

From `backend`:

```bash
python -m pytest tests app/validation/tests -q -ra --junitxml=backend-results.xml
```

From `frontend/UWA-3D-Print-Farm`:

```bash
npm run install:ci
npm test
npx tsc --project tsconfig.reports.json --noEmit
```

From `mockserver`:

```bash
python -m pytest tests -q -ra --junitxml=mock-results.xml
```

The frontend `npm test` command builds the application and runs `tests/*.test.mjs`. The optional `reports-browser.mjs` script is separate and needs its own execution record.

The PostgreSQL migration smoke test drops the public schema. Keep it disabled unless the selected database has been verified as disposable. Do not run it against client or shared data.

## 5. Evidence matrix

| Area | Available evidence | Limit |
| --- | --- | --- |
| Backend reporting | PR #115 reports 10 reporting tests passed and 145 passed, 1 skipped, 0 failures for its full suite. | Historical contributor report; not verified as a rerun of the October baseline. |
| Frontend reporting | PR #130 reports 16 report tests passed, a scoped TypeScript check, a successful build and local live-data checking. | Historical contributor report; final-release execution logs are not attached. |
| Backend and validator checks | Test-source links in Section 11. | Available assertions are not execution results. |
| Frontend and mock checks | Test-source links in Section 11. | Fixtures and stubs do not establish complete live integration. |
| Portal observations | Screenshots in Documents 01–03. | Support the captured views and displayed outcomes. |
| Mock-printer observations | Document 04 shows printing, ready, finished and paused states. | The paused capture uses a different job; removal gating and recovery are not established by these images. |
| Chatbot observation | Document 04 shows suggested questions and a pricing reply. | Records one displayed answer; does not establish comprehensive accuracy or provider configuration. |
| Client approval | Email reproduced in Section 10. | Confirms the MVP discussed on 11 August 2026; does not identify the October commit. |

## 6. Findings and outstanding verification

Document 05 records reported findings requiring confirmation or correction. This report does not classify them as reproduced test failures without supporting execution records.

Final automated suites, browser integration, PostgreSQL migrations, removal gating, recovery and intended external-service integrations require appropriate execution evidence.

## 7. GitHub CI evidence

The GitHub lookup for commit `019cc9945961afd3ef90e3568c7a1409b7b995a8` returned no workflow runs and no combined-status entries.

No CI pass was retrieved through those lookups. This does not establish that contributors never tested the project or that no evidence exists elsewhere.

## 8. Mock demonstration and physical-printer boundaries

Document 04 contains local mock-monitor observations. Simulator progress, temperatures and material values must not be presented as physical measurements.

Physical-printer commissioning evidence is not established by the supplied screenshots. Before real operation, record machine and firmware identity, network access, authenticated commands, reviewed sample printing, pause/resume, completion, removal gating and recovery behaviour under the site's operating procedures.

## 9. Final handover verification checklist

This checklist concerns final-release evidence. It does not replace or withdraw the client's earlier MVP approval.

| Check | Evidence to record | Status in this report |
| --- | --- | --- |
| Final release identity | Commit SHA and local changes, linked to the execution environment. | Baseline recorded; screenshot-session SHA not established. |
| Automated suites | Backend, validator, frontend and complete mock outputs with exit codes. | Final execution records not attached. |
| Installation and migrations | Clean installation and disposable PostgreSQL migration results. | Not established by the supplied evidence. |
| Authentication and permissions | Registration, verification, sign-in, logout and direct role-access checks. | Selected interface captures available; complete verification outstanding. |
| Submission and lifecycle | Validation, accepted submission, queue ordering, pause/resume, completion and removal gating. | Selected displayed states available; complete workflow verification outstanding. |
| Reporting | Known-data reconciliation, filters, user exploration and CSV output. | Historical PR results and selected screenshots available. |
| Help chatbot | Representative questions, follow-ups, errors and agreed data-handling requirements. | Suggested questions and one displayed reply captured. |
| Recovery | Isolated database/files restore and reconciliation. | Execution evidence not attached. |
| Physical operation | Machine-specific commissioning and operational approval, if required. | Not established in this report. |
| Final handover | Delivered scope, outstanding work and operational ownership. | Record separately from the August MVP approval. |

## 10. Client MVP approval and final handover record

Christopher Lamb provided written approval of Group 16's MVP on 11 August 2026. His email states: “I provide written confirmation that I approve Group 16's MVP.” It notes that the additional discussed items were for later work.

The email confirms approval of the MVP discussed at that stage. It does not identify the October implementation baseline or record final automated testing or physical-printer commissioning.

![Client email confirming Group 16's MVP approval](../screenshots/client-mvp-approval-2026-08-11.png)

**Figure 1 — Written MVP approval, 11 August 2026.**

| Approval record | Evidence |
| --- | --- |
| Client representative | Christopher Lamb |
| Approval date | 11 August 2026 |
| Approved item | Group 16's MVP as discussed at that stage |
| Approval reference | Email reproduced above |
| Commit specified in email | None |

Any later final-handover decision should record its date, release, agreed operating scope, outstanding actions and maintenance owner.

## 11. Repository evidence index

These pinned links identify test and implementation source. They do not independently establish execution results.

| Evidence | Pinned reference |
| --- | --- |
| Backend test suite and fixture isolation | [backend/tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests), [conftest.py](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/conftest.py) |
| Backend dependency manifest | [backend/requirements.txt](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/requirements.txt) |
| Validator suite and converter setup | [validator tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/validation/tests), [setup_bgcode.sh](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/validation/setup_bgcode.sh) |
| Frontend commands and locked installation | [package.json](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/package.json), [frontend directory](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm) |
| Frontend test suite and optional browser script | [frontend tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/tests) |
| Scoped reports type-check configuration | [tsconfig.reports.json](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/tsconfig.reports.json) |
| Mock tests, requirements and pytest configuration | [mockserver/tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/tests), [requirements.txt](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/requirements.txt), [pytest.ini](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/pytest.ini) |
| Destructive opt-in migration test | [test_alembic_smoke.py](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/test_alembic_smoke.py) |
| Public help route, history checks and reference cache | [help API](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/api/v1/help.py), [help_service.py](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/help_service.py) |
