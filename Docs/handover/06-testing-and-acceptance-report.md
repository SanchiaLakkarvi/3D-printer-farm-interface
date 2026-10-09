# Testing and Acceptance Report

**Group 16 — UWA 3D Printer Farm Interface**

| Document control | Details |
| --- | --- |
| Document version | 1.3 |
| Evidence review date | 9 October 2026 |
| Implementation baseline | `14cde47` |
| Automated execution date | 9 October 2026 |
| Environment | macOS, Python 3.11, Node 22, Docker Compose |
| Backend test result | 201 passed, 1 skipped, 0 failures |
| Selected mock-server test result | 12 passed, 0 failures |
| Frontend final-release check | Scoped TypeScript check passed |
| Client approval | Christopher Lamb approved Group 16's MVP in writing on 11 August 2026. See Section 7. |

---

## 1. Verification and Test Activities

We used **automated tests, manual checks, and mock-printer testing** to verify the main parts of the system.

Automated backend tests were used to check authentication and role access, printer and material management, print jobs, queue behaviour and timing, job history, reporting, error handling, and other backend functions. The repository also contains dedicated G-code validation tests, frontend tests, and tests for the mock-printer service.

A fresh backend test run was completed on **9 October 2026** against release commit `14cde47`. The backend suite completed with:

- **201 passed**
- **1 skipped**
- **0 failures**

Selected mock-printer tests were also executed and completed with:

- **12 passed**
- **0 failures**

A scoped frontend TypeScript check was also completed successfully against the release baseline.

Earlier development testing provides additional evidence. Backend reporting PR #115 reported **10 reporting tests passed** and a full backend result of **145 passed, 1 skipped, and 0 failures**. Frontend reporting PR #130 reported **16 reporting tests passed**, together with a successful scoped TypeScript check, frontend build, and local checking against live report endpoints.

We also carried out manual checks of important user workflows. These included registration and email verification, login and role access, G-code upload and validation, compatible printer selection, job submission, queue and history views, notifications, and usage reporting.

Because physical printers were not always available, the project includes a **mock printer service**. This allowed the team to test printer communication and simulated states such as printing, ready, finished, paused, job dispatch, and staff removal confirmation without depending on physical hardware.

### Test Area Summary

| Test area | Evidence |
| --- | --- |
| **Backend** | Automated tests for APIs, services, permissions, queue logic, job handling and reporting |
| **G-code validation** | Dedicated validator tests for supported files and compatibility rules |
| **Frontend** | Reporting tests, scoped TypeScript checking and historical build evidence |
| **Mock printers** | Selected automated tests and demonstrations of simulated printer states and communication |
| **Manual checks** | Registration, login, upload, validation, printer selection, queue, history, notifications and reports |

---

## 2. Final Release Test Execution Results

Fresh automated testing was completed against release commit `14cde47` on **9 October 2026**.

### Automated Test Results

| Test suite | Execution command | Result | Status |
| --- | --- | --- | --- |
| **Backend API and Logic** | `cd backend && .venv/bin/pytest tests` | **201 passed, 1 skipped, 0 failures** in 2.62s | **PASSED** |
| **Selected Mock Printer Tests** | `cd mockserver && ../backend/.venv/bin/pytest tests/test_prusalink.py tests/test_queue_demo_config.py` | **12 passed, 0 failures** in 0.67s | **PASSED** |
| **Frontend Type Check** | `cd frontend/UWA-3D-Print-Farm && npx tsc --project tsconfig.reports.json --noEmit` | **Type-check passed** | **PASSED** |

The mock-server result above applies to the selected test files that were executed. It is not presented as a complete run of every test under `mockserver/tests/`.

The frontend final-release command above verifies the scoped TypeScript configuration. The successful frontend build reported in PR #130 is retained as historical development evidence rather than being presented as part of this fresh final-release command.

### Historical Contributor Evidence

The final-release results build on earlier development testing:

- **Backend reporting — [PR #115](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/pull/115)**  
  Reported 10 reporting tests passed and a full backend result of **145 passed, 1 skipped and 0 failures**.

- **Frontend reporting — [PR #130](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/pull/130)**  
  Reported **16 reporting tests passed**, a scoped TypeScript check, successful frontend build, and local checking against live report endpoints.

These historical results support the development history but are kept separate from the fresh final-release execution above.

---

## 3. Test Environment and Boundaries

The automated test environment is designed for fast and repeatable development testing, but it does not reproduce every production condition.

### Backend

Backend pytest fixtures use **Fake Auth and an in-memory SQLite database** for local automated testing. Production deployment uses Supabase/PostgreSQL together with the project's database migrations.

This means the backend automated test results provide strong evidence for application logic, APIs, permissions, queue behaviour, reporting and error handling, but they do not by themselves prove all production PostgreSQL or Supabase behaviour.

### Frontend

Some frontend tests use controlled API responses and session data. These tests are useful for checking frontend behaviour in repeatable conditions but do not replace full live browser-to-backend testing.

### Mock printers

The mock printer service provides a PrusaLink-compatible environment for development and demonstration without physical hardware.

It can simulate:

- printer status;
- job dispatch;
- printing progress;
- pause and resume;
- completion;
- printer availability; and
- related application updates.

However, simulated progress, temperature, filament use and printer states are not physical measurements.

### Physical printers

Final physical Prusa-printer commissioning has **not yet been fully verified**.

Before real operation, machine-specific testing should confirm:

- printer and firmware identity;
- network connectivity;
- authentication;
- file transfer;
- print start;
- pause and resume;
- completion;
- physical print removal;
- next-job release; and
- recovery from printer or network failures.

---

## 4. Evidence Matrix

| Area | Available evidence | Qualification |
| --- | --- | --- |
| **Backend services** | 201 tests passed, 1 skipped, 0 failures | Fresh execution against release commit `14cde47` |
| **Backend reporting** | PR #115 — 10 reporting tests and historical full backend regression result | Historical development evidence |
| **G-code validation** | Validator test source under `backend/app/validation/tests/` | Dedicated validation coverage exists; keep separate from the 201-test result unless executed together |
| **Frontend reporting** | PR #130 — 16 reporting tests, TypeScript check and build | Historical development evidence |
| **Frontend final-release check** | Scoped TypeScript check | Fresh execution against release baseline |
| **Mock printers** | 12 selected automated tests passed | Applies to the selected mock test files executed on 9 October |
| **Portal workflow** | Manual checks and screenshots | Supports the visible workflows and interface states |
| **Client MVP approval** | Email from Christopher Lamb dated 11 August 2026 | Confirms the MVP discussed at that stage; not final-release acceptance |

---

## 5. Mock Demonstration and Physical-Printer Boundaries

The mock-printer environment was used to support development, testing and demonstrations when physical printers were not available.

The mock environment can exercise the software path for printer polling, queue dispatch, printing states, pause/resume, completion and staff removal confirmation.

The values produced by the simulator must not be presented as measurements from real printers. In particular:

- simulated temperatures are not physical temperatures;
- simulated filament usage is not measured material consumption;
- simulated printing time is not a guarantee of real print duration;
- simulated completion does not prove real print quality; and
- successful mock communication does not prove compatibility with every physical printer or firmware version.

Physical-printer commissioning therefore remains a separate handover activity.

See:

- `Docs/handover/04-mock-printer-and-chatbot-guide.md`
- `Docs/handover/05-risk-assessment-known-limitations.md`

---

## 6. Final Handover Verification Checklist

| Check | Evidence | Status |
| --- | --- | --- |
| **Final release identity** | Release commit `14cde47` | **Completed** |
| **Backend automated suite** | 201 passed, 1 skipped, 0 failures | **Completed — 9 Oct 2026** |
| **Selected mock tests** | 12 passed, 0 failures | **Completed — 9 Oct 2026** |
| **Frontend scoped type check** | `tsconfig.reports.json` check passed | **Completed — 9 Oct 2026** |
| **Authentication and RBAC** | Automated tests and selected manual/interface evidence | **Evidence available** |
| **G-code validation** | Validator test source and manual validation evidence | **Evidence available** |
| **Submission and queueing** | Backend tests, mock-printer environment and manual workflow evidence | **Evidence available** |
| **Reporting and analytics** | Backend tests, PR #115, PR #130 and interface screenshots | **Evidence available** |
| **Installation and database setup** | Docker, Supabase and Alembic instructions in Document 03 | **Documented; production-specific verification remains environment dependent** |
| **Help chatbot** | Implementation and selected demonstration evidence in Document 04 | **Implemented; full provider behaviour is environment dependent** |
| **Recovery and backup** | Procedures documented in handover material | **Further production verification recommended** |
| **Physical printer commissioning** | Machine-specific real-printer testing | **Outstanding — requires physical hardware** |
| **Final client handover** | Final release review and operational ownership | **To be recorded separately from August MVP approval** |

---

## 7. Client MVP Approval and Final Handover Record

Christopher Lamb provided written approval of Group 16's MVP on **11 August 2026**.

His email states:

> “I provide written confirmation that I approve Group 16's MVP.”

The email confirms approval of the MVP discussed with the client at that stage. It does **not** identify release commit `14cde47`, confirm the final October test results, or record physical-printer commissioning.

![Client email confirming Group 16's MVP approval](../screenshots/client-mvp-approval-2026-08-11.png)

**Figure 1 — Written MVP approval, 11 August 2026.**

| Approval record | Evidence |
| --- | --- |
| **Client representative** | Christopher Lamb |
| **Approval date** | 11 August 2026 |
| **Approved item** | Group 16's MVP as discussed at that stage |
| **Approval reference** | Email reproduced above |
| **Commit specified in email** | None |

Any later final-handover approval should record:

- the release/commit reviewed;
- the date;
- the agreed operating scope;
- remaining limitations;
- outstanding actions; and
- the person or team responsible for future maintenance.

---

## 8. Repository Test Evidence

The following repository locations contain the main testing and verification evidence.

### Backend

- [Backend test suite](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/14cde47/backend/tests)
- [Backend test fixtures](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/14cde47/backend/tests/conftest.py)
- [Backend requirements](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/14cde47/backend/requirements.txt)

### G-code validation

- [Validator tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/14cde47/backend/app/validation/tests)
- [BGCode setup](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/14cde47/backend/app/validation/setup_bgcode.sh)

### Frontend

- [Frontend project](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/14cde47/frontend/UWA-3D-Print-Farm)
- [Frontend tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/14cde47/frontend/UWA-3D-Print-Farm/tests)
- [Frontend package configuration](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/14cde47/frontend/UWA-3D-Print-Farm/package.json)
- [Reporting TypeScript configuration](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/14cde47/frontend/UWA-3D-Print-Farm/tsconfig.reports.json)

### Mock printer service

- [Mock-server tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/14cde47/mockserver/tests)
- [Mock-server requirements](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/14cde47/mockserver/requirements.txt)
- [Mock-server pytest configuration](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/14cde47/mockserver/pytest.ini)

### Related handover documents

- [01 — Client Handover Summary](01-client-handover-summary.md)
- [02 — User Manual](02-user-manual.md)
- [03 — Installation, Operations and Maintenance](03-installation-operations-maintenance.md)
- [04 — Mock Printer and Chatbot Guide](04-mock-printer-and-chatbot-guide.md)
- [05 — Risk Assessment and Known Limitations](05-risk-assessment-known-limitations.md)

### Historical pull-request evidence

- [PR #115 — Backend Reporting](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/pull/115)
- [PR #130 — Frontend Reporting](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/pull/130)

---

## 9. Remaining Verification

The project has strong automated and demonstration evidence for the software implementation. However, the following items should remain clearly recorded as outstanding or environment-specific:

1. **Physical Prusa printer commissioning**
2. **Production-specific Supabase/PostgreSQL behaviour**
3. **Production deployment and network configuration**
4. **Physical removal and recovery testing**
5. **Final client review of the October release**
6. **Operational ownership and maintenance handover**

These limitations are intentionally documented rather than presented as completed verification.