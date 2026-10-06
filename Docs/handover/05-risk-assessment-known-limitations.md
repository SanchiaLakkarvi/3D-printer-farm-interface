# Risk Assessment and Known Limitations

**UWA 3D Printer Farm Interface — Group 16**

| Document control | Details |
| --- | --- |
| Project team | Group 16 |
| Document | 05 — Risk Assessment and Known Limitations |
| Version | 1.2 |
| Document date and repository review date | 6 October 2026 |
| Reviewed branch | `main` |
| Reviewed commit | `019cc9945961afd3ef90e3568c7a1409b7b995a8` |
| Repository | [SanchiaLakkarvi/3D-printer-farm-interface](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface) |
| Assessment status | Handover assessment; ratings, priorities and responsible roles are proposals, not client-approved decisions. |

## Contents

1. [Scope and evidence](#1-scope-and-evidence)
2. [Rating method](#2-rating-method)
3. [Risk register](#3-risk-register)
4. [Known-limitations register](#4-known-limitations-register)
5. [Issue-report verification](#5-issue-report-verification)
6. [Prioritised deployment actions](#6-prioritised-deployment-actions)
7. [Ownership and risk acceptance](#7-ownership-and-risk-acceptance)
8. [Evidence references](#8-evidence-references)

## 1. Scope and evidence

This assessment covers the supplied student/staff portal, FastAPI backend, authentication adapters, PostgreSQL schema/migrations, uploaded-file storage, queue dispatcher, mock printers, help chatbot and development Compose configuration. It considers a transition from local demonstration to a persistent, multiuser client service and eventual physical-printer operation.

The delivered default printing demonstration uses mock printers. Risks involving unsafe physical starts, uncleared beds or actual machine faults apply **when physical hardware is introduced**; they are not claims that the simulator operates a real machine. The supplied stack is not a verified production deployment.

The assessment does not establish laboratory safety approval, compliance certification, a penetration-test result, a provider retention guarantee or release-specific client acceptance. Existing site procedures, actual hosting controls, provider account settings and physical-machine behaviour were not established by this repository review. No incident is alleged by any risk entry.

### 1.1 Evidence and verification boundaries

Implementation and configuration are the primary evidence. Tests establish what checks are written and how their fixtures work; an issue's open/closed state is not a test result. Source references S01–S15 are indexed in Section 8.

| Evidence category | Available evidence and limit |
| --- | --- |
| Recorded implementation | Section 8 links to implementation and configuration at commit `019cc9945961afd3ef90e3568c7a1409b7b995a8`. These references identify the assessment baseline; they do not establish that the local screenshot session used the same commit. |
| Local interface screenshots | Documents 01–04 include screenshots of selected portal pages, validation results, help replies and mock-printer states. Each capture supports the displayed state, not every related workflow or integration. |
| Reported source findings | The assessment records findings attributed to the linked source files. Retain these as confirmed findings only where the source comparison can be supported by review records. |
| Reported diagnostics | Execution records for the ConfigParser and isolated help-service diagnostics are not attached to this handover pack. Their reported outcomes remain unverified within the pack. |
| Automated tests | Referenced test files identify available checks. Their presence does not establish that the final release passes; execution results belong in Document 06. |
| Integration and operational acceptance | The supplied screenshots do not establish physical-printer commissioning, production hosting, clean database migration, backup/restore, concurrent dispatch safety or comprehensive provider acceptance. |
| Issues and pull requests | Issue descriptions and PR status provide context. Delivered functionality must be assessed against the recorded commit and appropriate verification evidence. |

**Reported implementation control:** migration `0002_queue_indexes_drop_queue_position` widens `alembic_version.version_num` to `VARCHAR(255)` before recording its long revision ID. Long IDs are therefore not classified as a current fresh-install defect. The baseline ID fits the initial column. The stale smoke-test assertion and URL-interpolation issue are separate findings.

Use the [User Manual](02-user-manual.md), [Installation, Operations and Maintenance Guide](03-installation-operations-maintenance.md) and [Mock Printer and Chatbot Guide](04-mock-printer-and-chatbot-guide.md) for operational detail. Reassess this document when the release commit, hosting model, hardware, provider settings or user population changes.

### 1.2 Mock and physical operating boundaries

| Operating aspect | Reviewed boundary |
| --- | --- |
| Local demonstration | The mock exposes a PrusaLink-compatible API and monitor for two configured models. Time, temperatures, progress and material values are simulated; accelerated completion is not a physical performance measure. |
| Fault demonstration | Setting mock `ERROR` or `ATTENTION` changes the reported state but does not itself stop the simulation thread. Resetting the mock does not reconcile backend job records. These controls exercise application responses, not a real machine's fault handling or safety interlocks. |
| Physical operation | The adapter needs each actual printer's supported API, credentials and network access. Compatibility, real upload/start outcomes, reconnect behaviour and physical readiness require machine-specific commissioning. |
| Removal and pickup | Software records an authorised staff confirmation. It cannot sense bed clearance or prove student receipt; safe handling and pickup arrangements remain operational responsibilities. |

The mock-monitor captures in Document 04 show printing, ready, finished and paused states. The paused capture belongs to a different job from the printing and finished captures. These images do not establish second-job removal gating, physical bed clearance or recovery after disconnection.

## 2. Rating method

The following is a simple proposed method for this handover. Ratings are qualitative assessments, not measured probabilities or forecasts of incident frequency.

### 2.1 Likelihood

| Score | Label | Meaning for the assessed operating scenario |
| --- | --- | --- |
| 1 | Unlikely | Requires unusual conditions; an implemented control limits ordinary exposure. |
| 2 | Possible | A plausible operating condition can expose the gap, or integration evidence is incomplete. |
| 3 | Likely | The stated condition is expected to arise in routine use of the unmodified configuration/workflow. |

### 2.2 Impact

| Score | Label | Potential consequence |
| --- | --- | --- |
| 1 | Minor | Local confusion or a short interruption, recoverable without significant data or operational loss. |
| 2 | Moderate | Service interruption, wasted print/operator time, unexpected charges, incorrect records or support intervention. |
| 3 | Major | Potentially unsafe physical operation, unauthorised privileged access, significant sensitive-data exposure or loss without a demonstrated recovery path. |

### 2.3 Remaining risk

**Score = likelihood × impact.** Likelihood and impact below are assessed **with the listed existing controls in place**. The remaining-risk field gives that score and the outstanding gap. Recommended controls are not credited as implemented, and no predicted post-action score is claimed.

| Score | Rating | Proposed treatment |
| --- | --- | --- |
| 1–2 | Low | Track and address through normal maintenance; retain evidence and ownership. |
| 3–4 | Medium | Agree treatment and verification before persistent deployment or explicitly record a justified acceptance. |
| 6–9 | High | Treat as a deployment gate for the affected operating mode until controlled and verified or formally decided by the authorised client. |

The same numerical score can have different causes. Physical safety, identity control and unrecoverable-data concerns warrant explicit review regardless of score. These proposed bands do not authorise the project team to accept laboratory or client business risks.

## 3. Risk register

Each entry separates controls present in the reviewed release from proposed actions. Proposed leads may need support from other roles; no named person or account ownership is assigned.

The Existing controls fields describe controls reported in the recorded implementation assessment. They do not mean those controls were exercised successfully in the screenshot session. Confirm source findings and record relevant test results before using this assessment to approve deployment.

### 3.1 Register overview

| ID | Risk | Remaining assessment | Proposed lead |
| --- | --- | --- | --- |
| R01 | Physical integration assumed to be established by mock results | High — 6 | Technical integration lead |
| R02 | Validated file/configuration differs from physical readiness | High — 6 | Print Farm operator |
| R03 | Premature removal confirmation or uncleared failed print | High — 6 | Print Farm operator |
| R04 | Duplicate/uncertain dispatch or incorrect reconnect reconciliation | High — 6 | Backend maintainer |
| R05 | Demo authentication/configuration used for real accounts | High — 6 | Deployment operator |
| R06 | Privileged identity, session or access lifecycle mishandled | High — 6 | Database/Auth administrator |
| R07 | Development endpoints and runtime exposed as a client deployment | High — 6 | Deployment operator |
| R08 | Credentials exposed through configuration, database or backups | High — 6 | Service/account owner |
| R09 | Uploaded files exhaust storage or remain outside expected lifecycle | Medium — 4 | Application maintainer |
| R10 | Database, Auth and files cannot be recovered consistently | High — 6 | Backup/recovery owner |
| R11 | Migration/test changes damage the wrong database or block release | High — 6 | Database administrator |
| R12 | Chatbot supplies incorrect or stale guidance | Medium — 4 | Help-content owner |
| R13 | Sensitive chat input leaves the intended boundary | High — 6 | Service/data owner |
| R14 | Public chatbot requests cause outages or unplanned API spend | Medium — 4 | Provider-account owner |
| R15 | Required external services/network become unavailable | Medium — 4 | Deployment operator |
| R16 | Rebuild/update changes dependencies or breaks recovery compatibility | Medium — 4 | Application maintainer |
| R17 | Placeholder/backend-only screens mislead operational expectations | Medium — 4 | Product/handover owner |
| R18 | Estimates/prototype payment mistaken for settled billing/measurements | Medium — 4 | Service/business owner |
| R19 | Historical documentation/tests mistaken for final acceptance | Medium — 4 | Release/verification lead |

### R01 — Unverified physical-printer integration

| Field | Assessment |
| --- | --- |
| ID | R01 |
| Risk | Mock success is treated as proof that the installed physical printers can be operated safely and correctly. |
| Cause | The connected demonstration uses PrusaLink-compatible mocks. Actual network reachability, firmware/API responses, storage and hardware configuration have not been commissioned in this review. |
| Consequence | Commands fail, states are misinterpreted, or an unintended/unsafe physical operation occurs when dispatch is enabled. |
| Likelihood | 2 — Possible when moving beyond the mock environment. |
| Impact | 3 — Major. |
| Existing controls | PrusaLink adapter has typed transport/auth/conflict errors, bounded HTTP timeout and per-printer URLs. Synchronisation skips maintenance-status printers; polling can be disabled. |
| Remaining risk | **High — 6.** A software contract and simulator cannot establish the actual machine/network behaviour. Mock fault/reset controls do not reproduce all physical failure or recovery states. |
| Recommended action | Keep physical dispatch disabled during commissioning. Verify identity, status, text/binary upload, storage, start, pause/resume, faults, completion, reconnect and removal gating on each intended machine/firmware with trained staff. Record actual acceptance evidence. |
| Proposed responsible role | Technical integration lead, supported by the Print Farm operator and site network owner. |
| Evidence | S03, S04; U01; issue #71. |

### R02 — File validation does not establish physical readiness

| Field | Assessment |
| --- | --- |
| ID | R02 |
| Risk | A file passing validation is treated as proof of safe, compatible physical execution. |
| Cause | Rules inspect file contents/metadata and configured profiles, not installed nozzles, material loading, machine condition, adhesion or the cleared bed. Backend-selected materials and mock spool values are independently configured. |
| Consequence | Wrong material/settings, damaged or failed prints, wasted resources or potentially unsafe physical operation. |
| Likelihood | 2 — Possible, particularly after hardware/material changes. |
| Impact | 3 — Major for physical operation. |
| Existing controls | Connected submission checks format/integrity, metadata, executable commands, limits and the two supported profiles; submission revalidates and enforces approved PLA/PETG type matching. Full BGCode executable checks require conversion. Mock validation adds configured command/profile/stock checks. |
| Remaining risk | **High — 6.** These controls reduce file-related errors but do not measure or certify the real setup. |
| Recommended action | Maintain verified slicer/profile settings and a staff readiness procedure. Confirm actual hardware/material before enabling each printer; test accepted and rejected files, including binary conversion, against the intended environment. Do not repair incompatible metadata merely to pass checks. |
| Proposed responsible role | Print Farm operator, supported by the validation/application maintainer. |
| Evidence | S02, S04; N01, U01. |

### R03 — Print-removal and failed-part clearance

| Field | Assessment |
| --- | --- |
| ID | R03 |
| Risk | The next print starts while a previous part/debris remains, or the student mistakes completion for confirmed pickup readiness. |
| Cause | **Collect** relies on staff judgment and a single action; there is no bed sensor or separate confirmation dialog. The dispatcher holds `completed` jobs, but not `failed` jobs when the printer reports a ready state. Student pickup is a separate unrecorded event. |
| Consequence | Physical collision/failed print, unsafe handling, incorrect readiness records or unclear collection arrangements. |
| Likelihood | 2 — Possible if handling/clearance is premature or undocumented. |
| Impact | 3 — Major for physical printing. |
| Existing controls | Any completed same-printer job blocks dispatch. Farmer/Admin authorisation protects collection; the database action locks the job, is idempotent once ready, records removal/readiness and notifies the owner. Completion notifies Farmer accounts that removal is needed. |
| Remaining risk | **High — 6.** The record proves an authorised action was made, not that the bed is physically clear. Failed-print clearance has no equivalent hold. |
| Recommended action | Establish safe cooling/removal/bed-preparation and pickup procedures. Introduce and verify an appropriate hold/clearance workflow for failed/stopped jobs before physical use. Assess a deliberate confirmation step or other appropriate safeguard for removal. |
| Proposed responsible role | Print Farm operator, with the backend/UI maintainer for workflow changes. |
| Evidence | S03; N02, N03, U01. |

### R04 — Dispatch duplication and uncertain printer outcomes

| Field | Assessment |
| --- | --- |
| ID | R04 |
| Risk | Multiple submissions/pollers or an interrupted upload/start produce duplicate jobs or a mismatch between the application's record and printer activity. |
| Cause | Each backend process starts a poller. Dispatch selects a waiting row, sends upload/start, then commits printing state without a shared dispatch owner or idempotency/reconciliation state. Submission has no Idempotency-Key contract. An unreachable printer leaves current job state unchanged until later readings. |
| Consequence | Duplicate or uncertain physical starts, incorrect failure/completion records and unsafe resubmission after recovery. |
| Likelihood | 2 — Possible under concurrency, transport uncertainty or restarts. |
| Impact | 3 — Major when physical dispatch is enabled. |
| Existing controls | Per-printer oldest-job ordering, active-state checks, completed-print hold, mock conflict response, typed transport/conflict handling and a 15-second grace for stale finished/stopped/idle readings. These are not a cross-process dispatch claim. |
| Remaining risk | **High — 6.** Concurrent and ambiguous outcomes have not been shown safe against real printers. No duplicate incident is asserted. |
| Recommended action | Use one dispatching instance pending a verified coordination design. Add guarded dispatch ownership, submission retry handling and an explicit uncertain-outcome/manual reconciliation process. Test interruptions before/after printer acceptance and database commit, plus real reconnects. |
| Proposed responsible role | Backend maintainer, supported by deployment and Print Farm operators. |
| Evidence | S02, S03; U04, N04; issue #123. |

### R05 — Demo mode used for persistent accounts

| Field | Assessment |
| --- | --- |
| ID | R05 |
| Risk | Real users/data are admitted using synthetic authentication, identities or printer inventory. |
| Cause | Native settings default to Fake Auth; the demo overlay forces it and synthetic accounts. Base Compose seeds synthetic inventory, even when a Supabase database is selected. Fake accounts/tokens are process memory; startup account definitions can set roles. |
| Consequence | Unauthorised privileged access, lost access after restart, role mistakes or contamination of client inventory/data. |
| Likelihood | 2 — Possible if the supplied demo configuration is adopted without review. |
| Impact | 3 — Major. |
| Existing controls | Supabase adapter is available; fake-account seeding is restricted to fake mode. Student registration forces the Student role. The seed skips when materials exist, limiting repeated inserts but not validating a client inventory. |
| Remaining risk | **High — 6.** Configuration determines the security boundary; renaming `APP_ENV` does not convert the demo into production authentication. |
| Recommended action | Separate demo/client data and configurations. Set and verify Supabase mode, disable synthetic accounts/inventory seeding for persistent use, inspect effective Compose overrides and test all roles against the intended Auth project. |
| Proposed responsible role | Deployment operator, with the Database/Auth administrator. |
| Evidence | S01, S05; N05. |

### R06 — Identity, permissions and session lifecycle

| Field | Assessment |
| --- | --- |
| ID | R06 |
| Risk | Staff roles are granted incorrectly, access cannot be recovered/revoked as intended, or token/session behaviour is misunderstood. |
| Cause | Staff Auth UUIDs must match application profiles; creation/deprovisioning is manual outside a working user-management screen. Browser tokens are held in sessionStorage; logout discards them locally. The portal has no refresh-token, password-reset or server-side logout-revocation workflow. |
| Consequence | Unauthorised staff actions, legitimate users locked out, or access continuing longer than an operator expects. |
| Likelihood | 2 — Possible under account changes, token expiry or manual provisioning. |
| Impact | 3 — Major for privileged access. |
| Existing controls | Bearer tokens are validated through the selected Auth adapter. Roles come from the database profile; backend hierarchy guards inventory/staff/report actions. Student job/history output and notifications are scoped to the current user. Passwords are not stored on `users`; registration cannot select staff roles. |
| Remaining risk | **High — 6.** These API controls do not supply the missing access-lifecycle operations or prove live provider settings. |
| Recommended action | Define supported staff provisioning, recovery and deprovisioning; verify UUID/role correspondence, least privilege, real expiry/rejection and provider-side revocation behaviour. Recheck protected APIs directly rather than relying on hidden UI buttons. |
| Proposed responsible role | Database/Auth administrator. |
| Evidence | S05, S06; P02, B01, N06, U02. |

### R07 — Development hosting and exposed operator endpoints

| Field | Assessment |
| --- | --- |
| ID | R07 |
| Risk | Development servers, mock controls or unsuitable origins are exposed as a persistent client service. |
| Cause | Compose publishes local ports on host interfaces, uses a frontend development server and local browser origins. Mock control/monitor routes do not require application login. TLS, production process supervision and dependency-readiness health checks are not supplied. |
| Consequence | Unauthorised simulator manipulation, access/connectivity problems, misleading health status or service interruption. |
| Likelihood | 2 — Possible if the development stack is publicly hosted unchanged. |
| Impact | 3 — Major where privileged/test controls or client data are exposed. |
| Existing controls | Protected application APIs use authentication/RBAC; CORS origins are explicitly configured. Demo PostgreSQL has a readiness health check. These controls do not authenticate mock controls or provide TLS. |
| Remaining risk | **High — 6.** `/health` is backend liveness, not validation of database, Auth, printers or help. Hosting/account controls outside the repo are unknown. |
| Recommended action | Design/test the production runtime, TLS/domain/origin configuration, restricted operator network, supervision, readiness checks and alerts. Keep mock APIs outside public client access. Do not use CORS as the sole access-control measure. |
| Proposed responsible role | Deployment operator. |
| Evidence | S01, S04, S07; U03. |

### R08 — Credential exposure

| Field | Assessment |
| --- | --- |
| ID | R08 |
| Risk | Provider, database or printer credentials are exposed through files, logs, access transfer or backups. |
| Cause | Operator configuration holds privileged server keys. Printer passwords are Text fields in the application database, without an application-layer encryption mechanism. Dumps and copied configuration can therefore contain sensitive values. |
| Consequence | Unauthorised provider/database/printer access or unplanned provider usage. |
| Likelihood | 2 — Possible during operational handling or excessive access. |
| Impact | 3 — Major. |
| Existing controls | Configured provider keys stay in backend settings; the help client does not receive the key. `PrinterOut` omits PrusaLink credentials. Secret-bearing environment files are excluded from the Docker build context/version-control workflow. These measures do not protect every copy or determine provider/database-at-rest protection. |
| Remaining risk | **High — 6.** Actual secret storage, access grants, rotation and backup encryption were not established. No exposed real credential is alleged. |
| Recommended action | Transfer access privately, assign account owners, restrict database/backups and adopt protected secret storage/rotation. Review safe log handling and whether application-layer protection for stored printer secrets is required. Verify actual hosting/provider controls. |
| Proposed responsible role | Service/account owner, supported by deployment and database administrators. |
| Evidence | S01, S05, S06, S10; R13 is the separate user-chat exposure path. |

### R09 — Upload accumulation and incomplete legacy lifecycle

| Field | Assessment |
| --- | --- |
| ID | R09 |
| Risk | Uploads fill disk or remain longer than intended, including files accepted through the unfinished backend-only path. |
| Cause | There is a per-file limit but no supplied total/per-user quota, scheduled expiry or orphan reconciliation. `/api/jobs/upload` accepts `.gcode/.gco` with a no-op content-validation hook and creates `pending_selection` using a different path layout. Failed files and unsuccessful deletion can remain. |
| Consequence | Submission/dispatch failures, excessive retention, storage outage or confusion about which uploads are printable. |
| Likelihood | 2 — Possible with ongoing use or repeated large submissions. |
| Impact | 2 — Moderate. |
| Existing controls | Authentication, 50 MiB per-upload limit, server-owned filenames/paths, connected-route validation/revalidation and some failure cleanup. Staff readiness attempts successful-file deletion after commit. Legacy storage helpers check path containment. |
| Remaining risk | **Medium — 4.** The legacy endpoint does not directly bypass the connected workflow into printing; it stores unvalidated pending data and lacks a complete connected lifecycle. Cleanup remains best-effort. |
| Recommended action | Restrict/disable or complete the legacy route before exposing it for client use. Agree retention/quota rules, disk alerts and safe reconciliation of unreferenced files. Never delete files needed by waiting/running jobs merely to free space. |
| Proposed responsible role | Application maintainer, supported by the storage/deployment operator. |
| Evidence | S02, S08; B02, N07. |

### R10 — Inconsistent or unavailable recovery

| Field | Assessment |
| --- | --- |
| ID | R10 |
| Risk | A database/filesystem/provider loss cannot be recovered into a coherent working service. |
| Cause | Application records, local upload bytes and Supabase Auth identities are separate assets. The repository supplies no scheduled paired backup or executed restore drill. Demo-volume removal and mock recreation have different persistence scopes. |
| Consequence | Missing queued files, lost history/profiles, mismatched Auth UUIDs, duplicated/replayed jobs or unrecoverable service data. |
| Likelihood | 2 — Possible under failure, reset or an incomplete backup. |
| Impact | 3 — Major. |
| Existing controls | Demo PostgreSQL uses a named volume; backend uploads use a host bind mount. These preserve data across some restarts, not host/volume deletion. Foreign keys help maintain stored relationships. Provider-managed recovery settings are unknown. |
| Remaining risk | **High — 6.** Persistence is not demonstrated recoverability; a public-schema dump alone does not include Supabase Auth identities or uploaded files. |
| Recommended action | Agree recovery targets and ownership. Capture consistent database, full storage root, release/configuration and identity recovery; protect backups. Restore into an isolated target with dispatch/seeding disabled, verify Auth/file correspondence and reconcile physical jobs before switching service. |
| Proposed responsible role | Backup/recovery owner, with Database/Auth and deployment administrators. |
| Evidence | S01, S05, S08; U05; operational recommendations in document 03. |

### R11 — Database migration and destructive-test handling

| Field | Assessment |
| --- | --- |
| ID | R11 |
| Risk | A migration/test is aimed at the wrong database, damages data or produces misleading release verification. |
| Cause | The optional smoke test drops `public` with `CASCADE` and only rejects URLs containing `supabase.co`; other/shared URLs are not comprehensively excluded. Its expected head is stale. Alembic passes percent-encoded URLs unescaped to ConfigParser. Stamping/downgrading requires schema knowledge. |
| Consequence | Loss of the target schema/data, blocked upgrade or false interpretation of a test failure/version record. |
| Likelihood | 2 — Possible when selecting targets or using encoded credentials. |
| Impact | 3 — Major because destructive actions can target persistent data. |
| Existing controls | Smoke test is opt-in; base Compose disables automatic migrations. Migration `0002` already widens the version column; the graph has a merge and single head. Demo startup exits on migration failure. |
| Remaining risk | **High — 6.** An opt-in flag/hostname substring is not proof that a database is disposable. The version-width issue is already controlled and is not included as a current defect. |
| Recommended action | Fix the URL-interpolation handling and smoke assertion. Require an explicitly isolated test database and strengthen destructive-test targeting. Verify fresh/upgrade migrations and recovery before a client migration; do not stamp `head` or downgrade merely to suppress errors. |
| Proposed responsible role | Database administrator, supported by the backend/release maintainer. |
| Evidence | S09; D01, D02; issue #93 verified as resolved in code. |

### R12 — Incorrect or stale chatbot guidance

| Field | Assessment |
| --- | --- |
| ID | R12 |
| Risk | Students receive misleading instructions or rely on a reply for an account/job/collection decision. |
| Cause | The provider is instructed to use the help source, but answers are not independently checked against it. The source is cached until process reset; UI/history and file updates can leave older advice in context. |
| Consequence | Wrong troubleshooting, repeated submissions, collection confusion or delayed staff intervention. |
| Likelihood | 2 — Possible; no accuracy guarantee or live-answer certification is established. |
| Impact | 2 — Moderate. |
| Existing controls | One bounded reference, reference-only prompt, concise output limit and staff escalation instruction. The service cannot inspect accounts/files/jobs, execute printer actions or take payment; missing source fails closed. |
| Remaining risk | **Medium — 4.** Grounding instructions reduce scope but do not ensure answer accuracy. A long answer can also break the next request's history contract. |
| Recommended action | Assign a content owner. Review reference text against the release, restart/redeploy after edits, begin fresh browser conversations and check representative/unsupported questions. Fix the response/history length mismatch and provide a verified human contact route. |
| Proposed responsible role | Help-content owner, supported by the application maintainer. |
| Evidence | S10; D04, P03, N08. |

### R13 — Sensitive chatbot input and external transfer

| Field | Assessment |
| --- | --- |
| ID | R13 |
| Risk | A user submits personal information or a secret which is displayed/processed locally and may be sent to the provider. |
| Cause | Questions and selected history are sent to FastAPI; unmatched input and the full help source are forwarded to Anthropic. Regex checks cover selected formats, not every secret. Provider/account retention and infrastructure logging settings are not established by the code. |
| Consequence | Sensitive-data exposure or handling inconsistent with the client's requirements. |
| Likelihood | 2 — Possible when users paste troubleshooting details. |
| Impact | 3 — Major for real credentials or sensitive information. |
| Existing controls | Visible warning, bounded inputs/history, checks on both question and history, and local refusal before provider invocation for matched patterns. No chat-specific database/transcript writer is present; the help client does not attach the account token/profile. |
| Remaining risk | **High — 6.** Detection is incomplete; the browser has already sent text to the backend. Refused messages can remain in browser component state. Absence of a transcript writer is not a provider-retention or infrastructure-logging guarantee. |
| Recommended action | Verify provider data-use/retention and deployment logging requirements, communicate suitable input boundaries and keep the reference free of secrets. Test harmless synthetic patterns, define real-exposure handling and review stronger controls where needed. Do not promise all sensitive content is blocked. |
| Proposed responsible role | Service/data owner, supported by the provider-account owner and application maintainer. |
| Evidence | S10; N08, U06. |

### R14 — Public chatbot availability, abuse and API costs

| Field | Assessment |
| --- | --- |
| ID | R14 |
| Risk | Anonymous usage, shared-IP limits or provider failure causes unavailable help or unplanned charges. |
| Cause | The route requires no session; the limiter is per observed IP in one process. Restarts reset it, multiple workers have separate allowances and many IPs are not one quota. The adapter ignores returned usage metadata and supplies no spend cap/ledger or provider fallback. |
| Consequence | API spend beyond the agreed budget, denied help for legitimate users or service-support overhead. |
| Likelihood | 2 — Possible with exposed use or provider/account changes. |
| Impact | 2 — Moderate; actual budget/exposure is not known. |
| Existing controls | Default ten requests in the preceding sixty seconds, message/history limits, 400 output tokens, bounded provider timeout and structured `429`/`503` errors. The rest of the portal remains accessible when help is unavailable. |
| Remaining risk | **Medium — 4.** Limits bound some requests, not monthly expenditure, user identity or distributed abuse. Missing key/model/billing/outage causes are not distinguished by the user message. |
| Recommended action | Assign account/budget ownership, use verified provider spending controls, monitor status/latency/usage and validate client-IP handling behind the actual proxy. Design shared limiting before adding instances and define outage/escalation handling. |
| Proposed responsible role | Provider-account owner, supported by the deployment operator. |
| Evidence | S10; N08, U06. |

### R15 — External-service and network availability

| Field | Assessment |
| --- | --- |
| ID | R15 |
| Risk | A required database/Auth/email/printer/provider or build dependency is unavailable or misconfigured. |
| Cause | Normal operation depends on Supabase PostgreSQL/Auth/email settings and network access; physical printing needs the site network and printer API. Help uses Anthropic. Builds fetch external images/packages and pinned Prusa sources; full binary validation depends on converter tooling. |
| Consequence | Login/verification, submission, reporting, dispatch, help or rebuilding becomes unavailable; printing already accepted by a physical machine may continue without monitoring. |
| Likelihood | 2 — Possible. |
| Impact | 2 — Moderate; physical reconciliation is additionally covered by R04. |
| Existing controls | Adapter timeouts/error mapping, printer offline/error states, converter-required validation, startup failure on migration/seed errors and demo database health check. |
| Remaining risk | **Medium — 4.** Static liveness is not dependency readiness. No delivered alerting, fallback hosting or verified provider/site availability arrangement is established. |
| Recommended action | Verify provider/project access, email delivery/code template, endpoint/network reachability, converter builds and model access. Add dependency-aware monitoring, service ownership and recovery/escalation arrangements appropriate to the intended deployment. |
| Proposed responsible role | Deployment operator with the relevant service/network owners. |
| Evidence | S01, S02, S04, S05, S10, S11; U01–U03, U06. |

### R16 — Dependency drift, updates and rollback

| Field | Assessment |
| --- | --- |
| ID | R16 |
| Risk | Rebuilding/updating a release changes behaviour or the previous code cannot operate the newer database/files. |
| Cause | Python requirements use ranges without a full lock; container tags are not pinned by digest. Migrations change/drop fields; there is no supplied automatic rollback or executed recovery runbook. |
| Consequence | Regression, build failure, longer outage or data/format incompatibility on rollback. |
| Likelihood | 2 — Possible. |
| Impact | 2 — Moderate; irrecoverable loss is covered by R10/R11. |
| Existing controls | Frontend has a committed lockfile used by `npm ci`; Prusa sources are pinned to commits; migration revisions and repository history identify code changes. |
| Remaining risk | **Medium — 4.** A Git SHA alone does not fix every resolved dependency or ensure a downgrade is safe. No vulnerability scan or dependency security guarantee is claimed. |
| Recommended action | Record images/digests and resolved dependencies, review upgrades, test disposable migrations/workflows and retain paired recovery points. Verify backward compatibility or restore into an isolated target before rollback. Avoid untested broad dependency updates. |
| Proposed responsible role | Application maintainer, with the release and database operators. |
| Evidence | S09, S11; U03, U05. |

### R17 — Incomplete operational screens/capabilities

| Field | Assessment |
| --- | --- |
| ID | R17 |
| Risk | The client expects management, pickup, reprint or support actions that a visible page/description does not implement. |
| Cause | **Maintenance**, **Users & access** and **Help & support** are placeholder screens; inventory editing is backend-only. Physical pickup/packing, QR tracking and a connected reprint/cancel workflow are not delivered by the current portal. |
| Consequence | Staff cannot perform an expected task, take unsupported manual action or misunderstand the handover scope. |
| Likelihood | 2 — Possible when labels are mistaken for complete workflows. |
| Impact | 2 — Moderate. |
| Existing controls | Connected queue/history, pause/resume, removal/readiness, notifications and staff analytics are separately implemented; supported administrator APIs provide some inventory operations. |
| Remaining risk | **Medium — 4.** A data model, adapter method or placeholder description does not supply an end-to-end user action. |
| Recommended action | Review the limitations register with the client, label/restrict placeholders and agree supported manual procedures. Prioritise only the management/follow-up functions needed for the intended service and verify them before representing them as complete. |
| Proposed responsible role | Product/handover owner, supported by application and Print Farm operators. |
| Evidence | S03, S06, S07, S12; P01–P04, B01–B04, N02–N04. |

### R18 — Indicative metrics and payment prototype

| Field | Assessment |
| --- | --- |
| ID | R18 |
| Risk | Estimated/synthetic usage, indicative costs or retained Stripe code are treated as final measurement, revenue or a delivered billing service. |
| Cause | Mock time is accelerated; successful filament is copied from the estimate. Reports can use estimated values when actual values are absent. The connected upload flow does not take online payment; the retained checkout route uses a fixed amount/duration and does not enforce test-key use. |
| Consequence | Misleading billing/resource decisions, disputed amounts or inappropriate activation of a prototype. |
| Likelihood | 2 — Possible if demonstration values/prototype code are adopted without review. |
| Impact | 2 — Moderate; no charge or billing incident is asserted. |
| Existing controls | Connected upload shows estimates and states that online payment is not taken. Report APIs require Farmer/Admin access; frontend CSV logic quotes values and neutralises recognised formula-leading text. |
| Remaining risk | **Medium — 4.** Reporting controls do not establish metered consumption or an approved University pricing/currency/payment policy. A provider key would require separate review of the prototype route. |
| Recommended action | Confirm rate/currency/charging policy and distinguish estimates from measurements. Leave unused checkout disabled/restricted until an authorised billing integration, authentication, amounts and reconciliation are designed and tested. Validate real telemetry before using reports for final charges. |
| Proposed responsible role | Service/business owner, supported by reporting and application maintainers. |
| Evidence | S03, S12, S13; P04, N09, U07. |

### R19 — Inaccurate release and acceptance evidence

| Field | Assessment |
| --- | --- |
| ID | R19 |
| Risk | Historical issue descriptions, test counts or documentation are used to claim current functionality/acceptance. |
| Cause | `testing.md` still describes Usage reports as a placeholder, says the second job starts automatically after completion and lists historical expected failures/counts. Some tests use modified SQLite schemas or mocked services; the migration smoke head is stale. |
| Consequence | Incorrect client instructions, missed regressions or an unsupported claim of deployment readiness. |
| Likelihood | 2 — Possible if the release is not reviewed and rerun consistently. |
| Impact | 2 — Moderate. |
| Existing controls | Versioned source/tests, written role/scope checks, job-control/dispatcher tests and frontend report/help tests are available for a recorded release review. |
| Remaining risk | **Medium — 4.** Test presence, issue closure and old demonstrations do not certify the current release or establish client approval. |
| Recommended action | Correct contradictory documentation, rerun appropriate suites and clean integration checks against the final commit, record environment/actual outcomes and separate client acceptance evidence from technical checks. Reassess risks after fixes/new merges. |
| Proposed responsible role | Release/verification lead. |
| Evidence | S09, S14, S15; D02, D05; Section 5. |

## 4. Known-limitations register

A limitation states a current boundary or finding; it is not automatically a vulnerability, defect or accepted requirement. Categories are kept separate:

- **Placeholder:** visible screen/copy with no connected action for the advertised purpose.
- **Backend-only:** code/API/model exists, but the full portal workflow is absent or incomplete.
- **Untested integration:** relevant implementation exists, but current environment-specific acceptance evidence was not established.
- **Reported defect or inconsistency:** a specific finding attributed to source inspection or a diagnostic. Its supporting evidence and confirmation status must be recorded before treating it as a verified release defect.
- **Other limitation:** missing capability, design boundary or externally unknown condition.

### 4.1 Placeholder and prototype screens

| ID | Current limitation | Verification/evidence | Linked risks |
| --- | --- | --- | --- |
| P01 — Placeholder | **Maintenance** renders the generic feature panel; it does not record maintenance/downtime or edit machine status. | Current `Feature` selection and panel; maintenance data model does not connect that screen. S07, S06. | R03, R17 |
| P02 — Placeholder | **Users & access** cannot create staff, grant/revoke roles or manage accounts. | Generic feature panel; no staff-user management API/CLI in the reviewed workflow. S05, S07. | R06, R17 |
| P03 — Placeholder | **Help & support** does not supply a working contact/help page. The separate **Ask Print Farm help** dialog is connected. | Frontend branches and chatbot component. S07, S10. | R12, R17 |
| P04 — Static/prototype | **Usage & costs** explains the rate but is not a personal billing ledger. Unmounted prototype upload/payment UI and a retained checkout route are not connected payment acceptance. | Current feature rendering and checkout code; connected live upload is selected instead. S07, S13. | R18 |

**Working features are not classified as placeholders:** queue/history and Farm operations, Notifications/bell, live upload validation/submission and **Usage reports** have connected implementations. Their scope/verification limits still apply.

### 4.2 Backend-only or incomplete capabilities

| ID | Reported finding | Evidence basis and confirmation status | Recommended correction |
| --- | --- | --- | --- |
| B01 — Backend-only | Administrator printer/material creation/update and printer deletion use APIs. No complete inventory editor or staff-account creation workflow is connected in the portal. | Protected inventory routes and placeholder selections; manual Auth/profile correspondence is required for staff. S05–S07. | R06, R17 |
| B02 — Incomplete backend route | `/api/jobs/upload` creates unvalidated `pending_selection` rows after extension/size checks. Its content hook is a no-op; its relative storage keys differ from the connected dispatch/collection path handling. | Reviewed upload/storage code. It is not automatically dispatched as a validated job and is not the live frontend submission route. S02, S08. | R09 |
| B03 — Model only | Maintenance records and `collection_records.collected_at` exist in the schema, but the portal does not record maintenance or actual student pickup through them. | Models/routes and UI; staff **Collect** records removal/readiness instead. S03, S06, S07. | R03, R17 |
| B04 — Adapter only/legacy API | The printer adapter has a stop method, but there is no connected portal cancel/stop workflow. Legacy token-hash confirmation remains an endpoint, while current registration uses signup-code verification. | Adapter/job/auth routes and UI. Do not infer a staff stop screen or link-confirmation screen from those methods. S03, S05, S07. | R04, R06, R17 |

### 4.3 Integrations without current acceptance evidence

| ID | Integration boundary | Evidence still required | Linked risks |
| --- | --- | --- | --- |
| U01 — Physical printers | PrusaLink-compatible adapter and mocks exist; specific UWA machines/network/firmware are not commissioned by this review. | Real status/upload/start/pause/resume/fault/reconnect/removal checks with trained staff and recorded machine versions. S03, S04. | R01–R04 |
| U02 — Hosted Auth/email | Supabase adapter and signup codes are implemented. Fake/mocked tests do not prove delivery, confirmation, staff provisioning, expiry or provider account settings. | Live checks against the intended Auth project and permitted recipients; recovery/deprovisioning procedure. S05, S14. | R05, R06, R15 |
| U03 — Production hosting | Docker development stack and hosting scaffolding exist; D1/R2 are unset and the application uses backend PostgreSQL. | Selected production runtime, domains/TLS/origins, private control network, supervision and dependency-aware checks. S01, S07. | R07, R15, R16 |
| U04 — Concurrency/recovery | Single-process polling and typed errors exist; multi-instance coordination and uncertain printer outcomes are not accepted. | Concurrent/interrupted dispatch and submission-retry tests, plus real-state reconciliation. S02, S03. | R04 |
| U05 — Backup/restore | Persistence mappings and migration code exist. Application backups/recovery are recommendations, not supplied verified automation. | Consistent database/Auth/files recovery drill with dispatch disabled and measured recovery targets. S01, S08, S09. | R10, R11, R16 |
| U06 — Live chatbot/provider | Provider adapter, reference and limits exist. Live accuracy/availability/account spend and retention requirements are not verified. | Representative answers, actual provider/model access, proxy rate scope, budget ownership and confirmed data-handling settings. S10. | R12–R15 |
| U07 — Billing | Indicative pricing/reporting and retained checkout code exist. Approved charging/payment/reconciliation is not delivered or accepted. | Client billing policy and a separately tested integration if required. S12, S13. | R18 |

### 4.4 Findings requiring confirmation or correction

| ID | Reported finding | Evidence basis and confirmation status | Recommended correction |
| --- | --- | --- | --- |
| D01 — Reported configuration defect | Percent-encoded `DATABASE_URL` may fail Alembic configuration if `%` is passed to ConfigParser unescaped. | The assessment reports an unescaped URL configuration call and a synthetic ConfigParser failure. Diagnostic output is not attached; confirm the code path and reproduce the result before marking this finding verified. S09. | If confirmed, correct URL handling at the configuration boundary while retaining valid credential encoding, and add an encoded-URL regression check. |
| D02 — Reported test inconsistency | The smoke test reportedly asserts `0007_merge_queue_upload`, while the recorded migration head is `0008_job_pause_notifications`. | The assessment attributes this finding to inspection of migration revisions and the test assertion. Confirm both against the recorded commit. S09. | If confirmed, update or derive the expected head and run the test only against an explicitly disposable PostgreSQL database. |
| D03 — Reported optional build inconsistency | The optional `queue-demo` build context reportedly differs from the repository-root layout expected by the backend Dockerfile. | The assessment reports a Compose/Dockerfile path comparison. No Docker build result is attached; confirm the effective build configuration and reproduce the optional-overlay build. S01. | If confirmed, align the build context and Dockerfile paths, then verify the optional overlay. |
| D04 — Reported chat contract defect | A provider reply over 1,000 characters may be returned successfully but rejected as history on the next request. | The assessment reports that a synthetic 1,049-character reply was rejected when reused as history. Execution output is not attached; reproduce the long-reply follow-up before marking this finding verified. S10. | If confirmed, align response and history length handling, and add a long-reply follow-up check across the client and service. |
| D05 — Reported documentation inconsistency | `testing.md` reportedly describes Usage reports as a placeholder, omits the completed-job removal hold and presents historical test counts or expected failures. | The assessment attributes this finding to comparison with the reports interface and dispatcher. Confirm these differences against the recorded commit. Historical counts are not current test results. S03, S07, S15. | Correct confirmed differences, distinguish completion, removal confirmation and pickup, and label test results with their actual release and execution date. |

No other risk is presented as a verified exploit, incident or guaranteed failure. In particular, the historical long-revision-column problem is addressed by the current `0002` migration and is excluded from this defect list.

### 4.5 Other boundaries and unknowns

| ID | Current boundary | Implication/evidence | Linked risks |
| --- | --- | --- | --- |
| N01 | Only the CORE One HF0.4 and XL 5T Input Shaper 0.4 backend profiles are configured; approved submission material types are PLA/PETG. | Other hardware/material settings need deliberate profile validation/commissioning. Multiple mock tools do not establish a complete multimaterial portal workflow. S02, S04. | R01, R02 |
| N02 | Printing completion, staff removal/readiness and student pickup are separate events. | **Collect** means staff confirms removal and marks ready; it does not record student receipt. S03. | R03, R17 |
| N03 | Failed jobs have no completed-print removal hold. | A ready-state failed printer can receive another waiting job; physical clearance requires a defined control before real operation. S03. | R03 |
| N04 | No QR tracking, submission Idempotency-Key contract or connected automatic reprint/cancel workflow is delivered. | Issue #123 is a follow-up request, not evidence those features exist. New resubmission creates another job. S02, S03. | R04, R17 |
| N05 | Fake-auth state is in memory; configured demo identities can be recreated, but arbitrary registrations are not durable Auth identities. | Backend restart invalidates fake sessions/access state while database profiles/jobs can remain. S01, S05. | R05 |
| N06 | No UWA SSO, portal password-reset/refresh-token workflow or server-side logout revocation is implemented. | Normal sign-in remains email/password; signup code confirms registration, not passwordless sign-in. Actual provider recovery is an operator responsibility. S05, S07. | R06 |
| N07 | No scheduled retention/orphan cleanup or global/per-user storage quota is supplied; successful-file deletion is best-effort. | Storage ownership/alerts and client retention/recovery policy remain to be established. S03, S08. | R09, R10 |
| N08 | Chat history/cache/rate state is process/browser-local; the chat has no live account/job access, universal secret detection, accuracy guarantee, usage ledger or provider-retention guarantee. | Frontend limits and backend settings must stay aligned; cached reference requires restart/redeployment after edits. S10. | R12–R14 |
| N09 | Durations, filament and costs include estimates/synthetic values; online slicing, live camera and remaining-filament application inventory are not connected features. | Do not present mock telemetry/report totals as audited physical measurements or delivered capabilities. S02–S04, S12. | R02, R18 |
| N10 | Submission-notification behaviour requires confirmation against the recorded commit. | Assess Farmer submission and completion/removal-needed notifications against the validated-submission and lifecycle code. Any changes merged after the recorded commit require an updated release baseline and verification before being included as delivered functionality. S02, S03. | R17, R19 |
| N11 | Actual provider backup/retention, host security, site network access, named operational owners and client acceptance records are unknown from the evidence inspected. | Obtain those details through handover and reassess the applicable ratings. Missing evidence is not proof that no controls exist outside GitHub. | R01, R07, R10, R13–R16, R19 |

## 5. Issue-report verification

The following reports are retained for traceability. Their descriptions can represent historical behaviour or requested future work. No reported test count is promoted to current certification.

| Report | Code comparison at the reviewed commit | Assessment outcome |
| --- | --- | --- |
| [#71 — Physical-printer connection](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/71) | Per-printer PrusaLink URLs/credentials and an adapter exist; the supplied demonstration inventory targets mocks. | Physical integration remains a commissioning/evidence gap. The issue is not proof that every intended machine is incompatible. |
| [#93 — Fresh database migration](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/93) | `0002` contains the documented `VARCHAR(255)` widening before recording the long ID. | Historical width problem has an implemented fix; do not list it as a current fresh-install defect. Full upgrade remains unexecuted here. |
| [#96 — Alembic app import](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/96) | `backend/alembic.ini` includes `prepend_sys_path = .`. | The reported missing import-path setup is addressed in configuration; not assumed to remain broken. |
| [#98 — Fault grace delay](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/98) | Error/attention handling precedes the 15-second grace check. | Historical deliberate delay is addressed; polling/transport time and simulator limitations still apply. |
| [#94 — Dispatch/lifecycle](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/94) | Dispatcher now holds completed jobs; successful backend-file deletion occurs in staff readiness, rather than at printing completion. | Report is partly superseded; current lifecycle code is authoritative. |
| [#1 — Mock server](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/1) and [#134 — Mock UI](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/134) | Mock service, PrusaLink facade and styled live monitor are present. | Open issue status is not proof they are missing or that every requested detail is accepted. |
| [#70 — OTP/integration](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/70) | Live queue/upload/report integration and signup-code verification exist; sign-in still requires email/password. | Historical request to remove password-based UX is not the current implemented authentication behaviour. |
| [#75 — Help chat](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/75) and [#76 — Safeguards](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/76) | Current source is `student-help.md`, not the older issue's `login-signup.md`. Reference prompt, checks, caps and rate limiter are implemented. | Recognise implemented controls with their actual limits; closure does not prove answer accuracy or comprehensive secret blocking. |
| [#123 — QR/retry tracking](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/issues/123) | Current routes/dispatcher lack the requested QR tracking, Idempotency-Key and uncertain-outcome workflow. | Verified as outstanding capability scope, not as a recorded duplication incident. |
| [PR #136 — Submission notifications](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/pull/136) | Confirm submission-notification behaviour against the recorded commit; PR status alone does not establish inclusion in that release. | Changes introduced after the recorded commit require an updated baseline and verification before being described as delivered. |

## 6. Prioritised deployment actions

These are **proposed gates and priorities**, not a client-approved release plan. Apply each gate to the relevant operating mode; local mock use does not constitute permission for physical deployment.

| Priority | Action and linked risks | Evidence needed to close the action | Proposed lead |
| --- | --- | --- | --- |
| P0 — Before any physical dispatch | Commission the actual printer/network/profile and establish completed/failed-part clearance. R01–R03. | Recorded machine/firmware identity, reviewed sample execution, failure/reconnect checks and staff removal/readiness procedure. | Integration lead + Print Farm operator |
| P0 — Before any physical dispatch | Control dispatch ownership and uncertain outcomes; keep one poller pending verified coordination. R04. | Interrupted/concurrent submission/dispatch tests and a supported manual reconciliation path without blind resend. | Backend maintainer |
| P0 — Before persistent client data | Separate demo/client configuration; verify real Auth, roles and private credential/access handling. R05, R06, R08. | Effective configuration, live role/identity checks, staff access-transfer/deprovisioning and secret-owner records. | Deployment + Database/Auth administrators |
| P0 — Before public/persistent hosting | Supply the selected production runtime, TLS, origins, private operator exposure and supervision. R07, R15. | Deployment review and dependency-aware operational checks; mock controls restricted. | Deployment operator |
| P0 — Before persistent data or schema change | Establish paired database/Auth/files recovery and isolate destructive migration tests. Confirm D01/D02 and correct any reproduced findings. R10, R11. | Successful isolated recovery drill and clean/upgrade PostgreSQL checks at the chosen release; protected target/backup records. | Database + backup owners |
| P0 — Before persistent public chatbot use | Confirm external data handling, account/budget owner, actual rate scope and human escalation route. R13, R14. | Provider/account requirements recorded, safe synthetic-input checks, spending/usage monitoring and verified support channel. | Service/data + provider-account owners |
| P1 — Before client pilot acceptance | Restrict/complete legacy uploads and set retention/quota/disk monitoring. R09. | Supported endpoint list, storage reconciliation checks and agreed retention operation. | Application/storage maintainers |
| P1 — Before client pilot acceptance | Confirm D03–D05, correct confirmed findings and test help reference/long-answer handling. R12, R19. | Optional overlay build if retained, meaningful help follow-up check and current instructions with actual dated results. | Application + verification leads |
| P1 — Before client pilot acceptance | Review placeholder/backend-only scope and indicative reporting/payment boundaries. R17, R18. | Client-reviewed feature matrix, supported operator procedures and separately agreed charging policy. | Product/service owner |
| P1 — Before client pilot acceptance | Record final release images/dependencies and run appropriate automated and integrated acceptance checks. R15, R16, R19. | Commit/environment/commands/outcomes, limitations and recovery-compatible release artifacts. | Release/verification lead |
| P2 — After a controlled pilot | Prioritise account-management, pickup tracking, QR/retry handling or other agreed follow-ups; reassess before scaling. | Approved scope, implementation and acceptance evidence for each newly introduced workflow. | Client product owner + maintainers |

Do not close an action solely because a PR was merged or a unit test passed. Record the evidence appropriate to its environment and consequence. No laboratory operating procedure is supplied or approved by this priority table.

## 7. Ownership and risk acceptance

At handover, the client should identify authorised owners for the repository/release, hosting, database/Auth, provider accounts, physical farm operations, help content and backups. The proposed roles above indicate the work to own, not who has already accepted it.

Maintain each risk with its treatment decision, assigned owner, evidence, target review date and updated remaining assessment. Changes to hardware/profile, Auth provider, hosting/exposure, worker count, file lifecycle, help source/model or dependency versions trigger reassessment.

Before a release is described as accepted, retain the actual technical results and the client's applicable acceptance decision, including any explicitly accepted limitations. The evidence inspected did not establish that decision for this release. This does not assert that no discussion or approval exists elsewhere; it identifies what remains to be supplied to the handover record.

## 8. Evidence references

All project implementation links below are pinned to commit `019cc9945961afd3ef90e3568c7a1409b7b995a8`. Issue/PR links in Section 5 are reports reviewed on 6 October 2026 and can change subsequently.

| Reference | Primary implementation/configuration evidence |
| --- | --- |
| S01 — Configuration/build | [Base Compose](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/docker-compose.yml), [demo](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/docker-compose.demo.yml), [optional queue overlay](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/docker-compose.queue-demo.yml), [backend Dockerfile](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/Dockerfile), [settings](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/core/config.py), [Docker ignore](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/.dockerignore) |
| S02 — Validation/submission | [Validator](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/validation/gcode_validator.py), [submission service](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/submission_service.py), [job routes](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/api/v1/jobs.py) |
| S03 — Dispatch/lifecycle | [Synchronisation and dispatcher](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/printer_sync_service.py), [job controls](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/job_control_service.py), [application lifecycle](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/main.py), [PrusaLink adapter](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/adapters/printer/prusalink.py) |
| S04 — Simulator | [Mock configuration](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/config/printers.yaml), [controls](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/app/main.py), [simulator](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/app/simulator.py), [worker](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/app/sdk_worker.py), [monitor](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/app/monitor.py) |
| S05 — Authentication/permissions | [API dependencies/RBAC](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/api/deps.py), [auth service](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/auth_service.py), [Supabase adapter](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/adapters/auth/supabase.py), [fake adapter](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/adapters/auth/fake.py), [auth routes](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/api/v1/auth.py), [browser session](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/lib/auth/session.ts) |
| S06 — Inventory/data scope | [Printer API](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/api/v1/printers.py), [material API](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/api/v1/materials.py), [printer model](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/models/printer.py), [safe response schema](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/schemas/printer.py), [job scope](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/job_service.py), [notification scope](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/notification_service.py), [collection model](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/models/collection_record.py) |
| S07 — UI/hosting | [Portal selections/placeholders](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/app/page.tsx), [live queue](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/components/farm/live-queue.tsx), [frontend Dockerfile](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/Dockerfile), [hosting scaffolding](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/.openai/hosting.json) |
| S08 — Storage | [Legacy upload](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/upload_service.py), [storage helpers](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/storage_service.py) |
| S09 — Migrations | [Migration revisions](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/alembic/versions), [implemented width fix](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/alembic/versions/0002_queue_indexes_drop_queue_position.py), [Alembic environment](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/alembic/env.py), [Alembic settings](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/alembic.ini), [destructive smoke test](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/test_alembic_smoke.py) |
| S10 — Chatbot | [Public route](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/api/v1/help.py), [service/cache/limits](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/help_service.py), [provider adapter](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/adapters/help/anthropic.py), [chat component](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/components/auth-help-chat.tsx), [help client](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/lib/help/client.ts), [help source](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/Docs/help/student-help.md) |
| S11 — Dependencies | [Backend requirements](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/requirements.txt), [mock requirements](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/mockserver/requirements.txt), [frontend manifest](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/package.json), [frontend lockfile](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/package-lock.json) |
| S12 — Reports | [Protected report routes](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/api/v1/reports.py), [report calculations](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/app/services/report_service.py), [reports UI](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/components/reports/usage-reports.tsx), [CSV/model logic](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/lib/reports/model.ts) |
| S13 — Payment prototype | [Retained checkout route](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/app/api/checkout/route.ts) |
| S14 — Test boundaries | [Fixture/schema substitutions](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/conftest.py), [RBAC tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/test_auth_rbac.py), [Supabase doubles](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/test_supabase_auth_adapter.py), [dispatcher tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/test_printer_sync.py), [staff-control tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/test_job_control.py), [help tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/backend/tests/test_help_chat.py), [frontend reports tests](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/frontend/UWA-3D-Print-Farm/tests/reports.test.mjs) |
| S15 — Historical instructions under review | [testing.md](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/blob/019cc9945961afd3ef90e3568c7a1409b7b995a8/testing.md). Used to identify documentation mismatches, not as current behaviour/test proof. |
