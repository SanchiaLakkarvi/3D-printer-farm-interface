# Spec: Authentication, Student Sign-up, and Seed Users

Domain vocabulary: `CONTEXT.md`. Decisions: `docs/adr/0001-supabase-auth-for-credentials.md`, `docs/adr/0002-single-users-profile-with-role.md`.

## Problem Statement

The print farm has no working Sign-in path. Students, Farmers, and Admins cannot authenticate; Roles are not enforceable on the API; and there is no way to demo Farmer/Admin behaviour with fixed accounts. The agreed login UI is a single page for everyone, but Role must come from the server profile—not from client-chosen “Sign in as …” buttons.

## Solution

Deliver email/password authentication via Supabase Auth, with one application User profile per person (shared UUID). Students self-register through Student Sign-up using a Student Email; Farmers and Admins are Seed Users (Christopher Lamb + three Farmers) with distinct passwords. After Sign-in, the API loads Role from the profile and enforces authorization. FastAPI remains the authority for protected actions; credentials never live in `auth_hash`.

## User Stories

1. As a Student, I want to Sign-up with first name, last name, Student Email, password, and department, so that I can access the print farm without an Admin creating my account.
2. As a Student, I want Student Sign-up to require an email of the form `{student_id}@student.uwa.edu.au`, so that only valid Student Emails can self-register.
3. As a Student, I want my Student Number to be derived from the Student Email local-part and stored on my profile, so that the system can verify and report on my student id.
4. As a Student, I want to Sign-in immediately after Sign-up (no Admin approval), so that I can use the system right away.
5. As a Student, I want Sign-up to reject non-Student Emails, so that Farmers and Admins cannot be created through self-registration.
6. As a Student, I want Sign-up to reject duplicate Student Emails, so that I cannot create two profiles for the same identity.
7. As a User, I want a single Sign-in page that accepts email and password for every Role, so that I do not need different login entry points.
8. As a User, I want Sign-in to succeed only with correct credentials, so that my account stays protected.
9. As a User, I want Sign-in to fail clearly with invalid credentials, so that I know authentication did not succeed (without leaking whether the email exists, where feasible).
10. As a User, I want my Role to be loaded from my profile after Sign-in, so that I never choose Farmer/Admin/Student at login.
11. As a User, I want the API to ignore any client-supplied Role claim, so that UI buttons cannot escalate privileges.
12. As a Farmer Seed User, I want to Sign-in with my seeded email and distinct password, so that I can exercise Farmer workflows in demos and tests.
13. As an Admin Seed User (Christopher Lamb), I want to Sign-in with my seeded email and distinct password, so that I can exercise Admin workflows in demos and tests.
14. As a developer, I want Seed Users (1 Admin + 3 Farmers) created in lockstep in Supabase Auth and the application profile, so that demos work before real staff emails exist.
15. As a developer, I want Seed User emails and passwords to be replaceable later, so that real Farmer/Admin credentials can replace placeholders without redesign.
16. As a Farmer, I want to submit print jobs on the same profile I use for Farmer actions, so that I do not need a second Student account.
17. As an Admin, I want Farmer capabilities and job submission on the same profile, so that I do not switch accounts to operate the farm or print.
18. As an Admin, I want Students to be distinguishable by Role `student`, so that permissions and reporting match the product language (not legacy `student_staff`).
19. As a User, I want my profile to expose first name and last name, so that the Sign-up form fields match stored identity.
20. As a Student, I want department captured at Sign-up, so that usage can be attributed later.
21. As a Farmer or Admin, I want Student Number to be optional (null) on my profile, so that staff accounts are not forced to invent a student id.
22. As a User, I want my application profile id to equal my Supabase Auth user id, so that identity linking is unambiguous.
23. As a User, I want a “current user / me” response after Sign-in, so that the client can show my name and Role without a second guess.
24. As a Student, I want protected Student actions to succeed only when my session is valid and my Role permits them, so that anonymous callers cannot act as me.
25. As a Farmer, I want Farmer-only endpoints to reject Students, so that collection/maintenance actions stay operator-only.
26. As an Admin, I want Admin-only endpoints to reject Students and Farmers, so that administration stays restricted.
27. As a security-conscious operator, I want passwords never returned in API responses or stored in the application `users` table, so that credentials stay in Supabase Auth only.
28. As a developer, I want automated tests to run without calling real Supabase Auth or real printers, so that CI stays safe and deterministic.
29. As a User, I want Sign-out (or session invalidation) behaviour defined at the API boundary, so that leaving a shared machine does not keep an active client session usable.
30. As a developer, I want schema migrations for Role rename, name split, nullable Student Number, and removal of `auth_hash`, so that the database matches the agreed auth model.
31. As a User with an existing session token, I want expired or invalid tokens rejected, so that stale sessions cannot call protected APIs.
32. As a Student, I want malformed Student Emails (wrong domain or empty local-part) rejected at Sign-up, so that bad data never becomes a profile.
33. As an Admin, I do not want self Sign-up to assign Role `farmer` or `admin`, so that privilege escalation via registration is impossible.
34. As a developer, I want documented Seed User emails (placeholders) and where passwords are supplied (env/seed config, not committed secrets), so that the team can demo safely.

## Implementation Decisions

### Architecture (from ADRs)

- Supabase Auth owns credentials and sessions; the application does not verify passwords against `users.auth_hash`.
- One `users` profile per person; profile `id` equals Supabase Auth user `id`.
- Roles: `student`, `farmer`, `admin`. No Student/Staff table split. Higher Roles retain lower capabilities on the same profile (Admin ⊃ Farmer ⊃ submit).
- Role is never accepted from the client at Sign-in or Sign-up (Sign-up always creates `student`).

### Schema changes

- Rename Role enum value `student_staff` → `student` (Postgres enum + ORM + docs that still say `student_staff` for this feature).
- Replace `name` with `first_name` and `last_name`.
- Rename `student_staff_number` → `student_number` (or equivalent); **nullable**; required for Role `student`; null for Farmer/Admin.
- Drop `auth_hash`.
- Keep unique `email`.
- Keep nullable `department` (required on Student Sign-up at the API validation layer).

### Auth integration

- Introduce a narrow Supabase Auth port/adapter: register user, sign in (issue session/JWT), validate token / get Auth user id. Production adapter talks to Supabase; tests use a fake.
- On Student Sign-up: validate Student Email → create Auth user → create `users` row with same UUID, Role `student`, derived Student Number, names, department.
- On Sign-in: Auth verifies email/password → load `users` by id → return session token plus safe profile fields (id, email, names, role, department, student_number).
- FastAPI dependencies: `get_current_user` from Bearer token; role guards for farmer/admin (and student where needed).
- Config: Supabase URL and service/anon keys via environment variables (server-only secrets never in responses or commits). Update `.env.example` with non-secret placeholders only.

### API surface (v1)

Exact paths may be adjusted to match router conventions, but behaviour must include:

- Student Sign-up (public): first_name, last_name, email, password, department.
- Sign-in (public): email, password → token + profile.
- Current user (authenticated): profile for the token subject.
- Optional Sign-out if Supabase session model requires server involvement; otherwise document client-side discard of token.
- At least one protected probe endpoint (or reuse a minimal authenticated route) so RBAC can be tested before other features land.

### Seed Users

- Create in Auth + `users`: Admin Christopher Lamb (`christopher.lamb@uwa.edu.au`, Role `admin`); Farmers `farmer1@uwa.edu.au` … `farmer3@uwa.edu.au` (Role `farmer`).
- Distinct password per Seed User; supply via local env/seed config—do not commit real passwords.
- Seed path is operational/demo tooling, not Student Sign-up.
- Seed profiles: null `student_number`; placeholder first/last names acceptable.

### Frontend

- Out of this backend-focused slice except: mockup Role buttons are **not** the auth model. When UI is built later, one Sign-in action; Role from `/me` (or equivalent).

### Modules (conceptual)

- Auth adapter (Supabase + fake).
- Auth/user service (Sign-up, Sign-in, profile load, Seed orchestration).
- API v1 auth routes + auth dependencies.
- Alembic migration for profile/Role changes.
- Tests at the HTTP seam with fake Auth.

## Testing Decisions

### What makes a good test

- Assert **external behaviour** at the HTTP API: status codes, response bodies, authorization outcomes.
- Do not assert internal SQLAlchemy call sequences, private helpers, or Supabase SDK details.
- No real Supabase Auth, no real printers, no real email in the default suite.

### Primary seam (agreed)

- **FastAPI `TestClient` against `/api` auth (and protected) routes**, with:
  - Fake Supabase Auth adapter injected for register/sign-in/validate.
  - DB session suitable for creating/reading profiles (extend beyond metadata-only tests as needed).

### Cases to cover

- Student Sign-up success → profile Role `student`, Student Number derived, immediate Sign-in works.
- Student Sign-up rejects wrong email domain / missing local-part / duplicate email.
- Student Sign-up cannot create farmer/admin.
- Sign-in success returns token + profile Role from DB.
- Sign-in failure on bad password.
- Authenticated `/me` (or equivalent) with valid token; 401 without/invalid token.
- Farmer-only route: Farmer OK, Student forbidden, Admin OK if hierarchy says Admin ⊃ Farmer.
- Admin-only route: Admin OK, Farmer/Student forbidden.
- Client-supplied Role in body/query does not change authorization.
- Schema/metadata or migration tests for enum rename, nullability, dropped `auth_hash`, name split (follow existing `test_schema_metadata` / alembic smoke patterns).

### Prior art

- `backend/tests/test_health.py` — TestClient HTTP smoke.
- `backend/tests/test_schema_metadata.py` — metadata constraints without live Supabase.
- `backend/tests/conftest.py` — extend with fake Auth + DB overrides as needed.
- `backend/tests/test_alembic_smoke.py` — opt-in migration smoke; keep refusing production Supabase URLs.

## Out of Scope

- Building the Next.js login/Sign-up UI (design reference only).
- UWA SSO / institution IdP.
- Admin invite email flows and Admin UI to provision Farmers.
- Admin approval gate before Student access.
- Self Sign-up for Farmers/Admins.
- Password reset / MFA / magic-link passwordless (unless already free from Supabase and explicitly added later).
- Non-student university staff self Sign-up (`@uwa.edu.au` without `student.`).
- Replacing Seed Users with real staff emails in production (manual/ops later).
- Full job/queue/printer features beyond a minimal protected probe for RBAC.
- RLS policy design for direct browser→Postgres access (FastAPI remains the write path).
- Publishing this spec as a GitHub issue (local file only per request).

## Further Notes

- Glossary: `CONTEXT.md`. Keep new docs/code aligned with Student, Farmer, Admin, Student Email, Student Number, Seed User, Sign-in, Student Sign-up, Supabase Auth.
- Existing code still has `student_staff`, `name`, `student_staff_number`, `auth_hash`, JWT settings aimed at app-issued tokens, and `passlib`/`python-jose`—reconcile with Supabase-session verification; remove unused password-hash paths once Auth adapter is in place.
- Login mockup “Sign In as Student / Operator / Admin” is illustrative only; Operator means Farmer in copy, not a Role.
- Seed passwords: distinct per user; document how developers obtain them locally without committing secrets.
- When implementing, update `Docs/Guides/database_schema.md` and any AGENTS.md Role mentions that still say `student_staff` for this area.
