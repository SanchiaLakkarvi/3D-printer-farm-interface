# Testing the demo: step by step

Simple steps to run the demo stack (UI, API, mock printers) and check that it works.
Run every command from the **repo root** (`3D-printer-farm-interface/`).

## 0. Start everything

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build -d
```

Wait about a minute, then open **http://localhost:5173**.

## 1. Log in (student, farmer, admin)

Three accounts are created **automatically every time the backend starts**, so they survive restarts.
Click the card that matches the role, then sign in:

| Role | Click this card | Email | Password |
|---|---|---|---|
| Student | **Student** | `00000002@student.uwa.edu.au` | `demo-password-1` |
| Farmer | **Printer Farmer** | `farmer.demo@uwa.edu.au` | `demo-password-1` |
| Admin | **Administrator** | `00000001@student.uwa.edu.au` | `demo-password-1` |

- The card has to match the account. A student email on the Administrator card says
  "This account does not match the access option you selected."
- One email is one role. To be a student **and** an admin, use two different emails.
- What each role sees: Student has 7 menu items. Farmer adds **Farm operations**, **Jobs** and
  **Maintenance**. Admin adds **Usage reports** and **Users & access** (still placeholders).

### Use your own emails and passwords
Create a file called `.env` in the repo root (it is git-ignored). It needs one line with **all**
the accounts you want. Format `email:password:role`, separated by commas. Roles are `student`,
`farmer`, `admin`. Passwords must not contain commas or colons.

```bash
DEMO_ACCOUNTS=12345678@student.uwa.edu.au:pick-a-password:student,farmer.demo@uwa.edu.au:demo-password-1:farmer,00000001@student.uwa.edu.au:demo-password-1:admin
```

Or write it with one command (change the password first):

```bash
printf 'DEMO_ACCOUNTS=12345678@student.uwa.edu.au:pick-a-password:student,farmer.demo@uwa.edu.au:demo-password-1:farmer,00000001@student.uwa.edu.au:demo-password-1:admin\n' > .env
```

Apply it (recreates only the backend; nothing else is touched):

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d backend
```

Check it worked. You should see one line listing your accounts:

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml logs backend | grep "Demo accounts"
```

The `.env` **replaces** the built-in list, so include every account you still want. If a listed email
already has a saved profile, it is reused, and its role and job history are kept.

### Promote an existing account (only if you skipped `.env`)
Change a role directly in the database, then sign out and back in on the matching card:

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml exec db psql -U printfarm -d printfarm \
  -c "update users set role='farmer' where email='someone@student.uwa.edu.au'"
```

Use `farmer` or `admin`. The account must have signed in at least once.

## 1b. Start clean: delete the database (no more messy sign-ups)

Use this when logins are in a mess (for example "409 already registered", or you just want an empty
farm with no jobs). It deletes **all** demo data: jobs, history, notifications, profiles.

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml down -v
docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d
```

Wait about 40 seconds. The database is rebuilt, the printers are re-seeded, and the three accounts
above (or the ones in your `.env`) come back by themselves. **You do not need to sign up again or
run any confirm command.**

Lighter options:
- **Only restart the backend** (keeps all data; the accounts return by themselves):
  `docker compose -f docker-compose.yml -f docker-compose.demo.yml restart backend`
- **Only clear the jobs** (keeps accounts and printers):
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.demo.yml exec db psql -U printfarm -d printfarm \
    -c "truncate notifications, job_validations, collection_records, print_jobs cascade"
  ```

### The other way: sign up by hand (rarely needed now)
Only for an email that is **not** in `DEMO_ACCOUNTS`.

1. Web app → **Student** → **Create a student account**. The email must look like
   `12345678@student.uwa.edu.au`. It says "Check your email", but no email is sent.
2. Confirm it yourself. The text after `confirm-` is your email in lower case:
   ```bash
   curl -X POST http://localhost:8000/api/auth/confirm-email \
     -H 'content-type: application/json' \
     -d '{"token_hash":"confirm-you@student.uwa.edu.au","type":"signup"}'
   ```
   Expect: `{"message":"Your email is verified. Sign in with your password."}`
3. Sign in with the email and password you chose.

Accounts made by hand are forgotten when the backend restarts. Add the email to `DEMO_ACCOUNTS`
to keep it, or use section 1b to start clean.

## 2. Test: print a file (student)

1. Log in as **Student** (section 1).
2. Click **Upload file**.
3. Choose this file: `raw/Rook1_0.4n_0.15mm_PLA_COREONE_1h5m.gcode`
4. Pick **PLA White**, then click **Submit to print queue**.
5. Click **View my jobs**.

You should see:
- `Printing` within a few seconds
- after about **1 minute**: it moves to **History** as `Completed`, cost **$2.04**

(The fake printer runs 60 times faster than a real one.)

## 3. Test: a bad file is rejected

1. **Upload file**
2. Choose: `backend/app/validation/data/broken_too_hot.gcode`

You should see **"This file can't be printed"** with a red reason. There is no Submit button.

## 4. Test: admin view

1. Click **Log out** (bottom of the left menu).
2. Click the **Administrator** card and log in as the admin (section 1).
3. Click **Farm operations**.

You should see both printers, the queue, and everyone's history.

## 5. Test: the printer breaks

1. Log in as Student and submit the file again (step 2).
2. While it says `Printing`, run:
   ```bash
   curl -X POST localhost:8080/control/printers/mock-coreone-01/fault \
     -H 'content-type: application/json' -d '{"state":"ERROR","reason":"test"}'
   ```
3. Look at **My jobs**. It should show **Failed** within a couple of seconds.
4. Fix the printer:
   ```bash
   curl -X POST localhost:8080/control/printers/mock-coreone-01/reset
   ```
   The printer goes back to **Available**.

## 6. Test: two jobs in a row (optional)

Submit the same file twice, quickly. The first says `Printing`, the second says `In queue`.
When the first finishes, the second starts by itself.

## 7. Run the automatic tests

```bash
cd backend && source venv/bin/activate && python -m pytest -q
```

Expected: about 138 passed, 1 skipped and **2 failed**. Both failures are known and unrelated to the demo:

- `test_real_coreone_bgcode_matches_core_one` needs Prusa's `bgcode` converter. Build it once with
  `bash backend/app/validation/setup_bgcode.sh` (needs CMake and internet; see `backend/app/validation/README.md`).
- `test_student_signup_pending_does_not_create_users_row` compares the allowed web origins with your local
  `backend/.env`, so it fails on some machines.

## 8. Something looks wrong?

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml ps       # is everything Up?
docker compose -f docker-compose.yml -f docker-compose.demo.yml logs backend
```

Ignore `host.docker.internal:9000 ... Connection refused` lines in the mock's log. They are harmless.

## 9. Stop

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml down -v
```

This also deletes the demo database, so the next start is clean (and the accounts are gone).

## 10. Prove the pieces are really talking to each other

Set this shortcut once per terminal (it saves typing):

```bash
dc() { docker compose -f docker-compose.yml -f docker-compose.demo.yml "$@"; }
```

**Easiest way: open the live monitor.** Go to **http://localhost:8080/monitor** in a second browser
window. Submit a file in the web app and watch the upload appear there, with the printer's progress
and temperatures counting up. (After pulling this change, rebuild the mock once:
`dc up --build -d mockserver`.)

**Frontend to backend.** Every click is an API call.
- In the browser: press **F12**, open **Network**, click **Fetch/XHR**. You will see
  `queue`, `printers` and `history` requests to `localhost:8000` every ~5 seconds.
  Uploading adds `validate` and `jobs`.
- Or in the backend log:
  ```bash
  dc logs -f backend | grep '/api'
  ```
  You should see lines like `"GET /api/jobs/queue HTTP/1.1" 200 OK`.

**Backend to mock printer.** The backend asks each printer for its status every 2 seconds.
```bash
dc logs -f mockserver | grep prusalink
```
You should see `GET /prusalink/mock-coreone-01/api/v1/status` twice in a row: first `401`, then `200`.
That pair is the password handshake (Digest login), so it proves the login worked.
When you submit a job you also see a `PUT .../api/v1/files/usb/<job id>.gcode`.

**The file really arrived.** The mock saves it under the job's id:
```bash
dc exec mockserver ls storage/mock-coreone-01
curl -s localhost:8080/control/printers/mock-coreone-01     # the mock's own view: state, file, progress
```
The file name (`b02db0c3-....gcode`) is the **same id as the job in the database**.

**The database.**
```bash
dc exec db psql -U printfarm -d printfarm -c "select left(id::text,8) job, status, printer_job_id, started_at, completed_at from print_jobs order by submitted_at desc limit 5"
dc exec db psql -U printfarm -d printfarm -c "select left(job_id::text,8) job, type from notifications order by sent_at desc limit 5"
dc exec db psql -U printfarm -d printfarm -c "select model, status, prusalink_url from printers"
```
`printer_job_id` is the number **the printer itself** reported for the job. The backend can only
know it by talking to the mock. `prusalink_url` is where each printer is contacted.

**Watch it live** (press Ctrl+C to stop). Submit a file while this runs:
```bash
while true; do clear
  dc exec -T db psql -U printfarm -d printfarm -c "select left(id::text,8) job, status, printer_job_id from print_jobs order by submitted_at desc limit 3"
  curl -s localhost:8080/control/printers/mock-coreone-01 | python3 -c "import sys,json;d=json.load(sys.stdin);print('mock:',d['state'],d['progress_percent'],'%')"
  sleep 2; done
```
You should see the job go `queued` to `printing` to `completed` while the mock counts 0 to 100 %.

**The quick proof: break the link.**
```bash
dc stop mockserver     # wait ~5 s: the printers turn Offline in the UI
dc start mockserver    # about 10 s later they are Available again
```
