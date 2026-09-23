# Queue demonstration

This optional local demo rotates three reusable student accounts: Engineering,
Architecture and Science. It submits the first job immediately, then one every
180 seconds, to the same seeded CORE One. The runner stops after 10 submissions
(27 minutes); queued jobs continue printing. No new account is created per job.

Start from the repository root, with the normal backend/.env setup described in
README.MD:

```sh
docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.queue-demo.yml up --build
```

The demo overlay uses the disposable local Postgres database and fake auth.
The queue overlay seeds the department accounts on every backend startup and
sets mock simulation speed to 1. It changes the sample G-code's duration comments
in memory to 3m 30s; the original sample is untouched. This modified file is for
the mock printer only. Preheating, file validation and polling add some time on
top of the 210-second printing phase.

Open http://localhost:5173 and sign in as `farmer.demo@uwa.edu.au` with password
`demo-password-1`. Open **Shared queue** to see filenames, departments, printer,
statuses and timing estimates. Open http://localhost:8080/monitor alongside it
to see printer progress and upload/start requests. Waiting jobs belong to the
backend; the mock reports the active print. The first waiting job should appear
around minute 3, before the first print finishes.

The student accounts are `90000001@student.uwa.edu.au` through
`90000003@student.uwa.edu.au`, with the same demo password. Each sees their own
jobs; the farmer sees all departments.

Stop new submissions without stopping printers:

```sh
docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.queue-demo.yml stop queue-demo
```

To run a custom number of jobs, start only db, mockserver, backend and frontend
with the command above, then run:

```sh
docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.queue-demo.yml run --rm queue-demo --base-url http://backend:8000 --count 5 --interval 180
```

Do not run a second generator while the first is active. Restarting the generator
adds another batch; it does not clear existing jobs. Stop the stack with the same
Compose files and `down`; the demo database and uploaded files remain.

Tests (from backend/):

```sh
python -m pytest tests/test_queue_demo.py tests/test_demo_accounts.py tests/test_printer_sync.py tests/test_queue_timing.py -q
```
