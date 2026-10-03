# Mock Server Technical Manual

## Purpose

Physical Prusa printers are not always available during development. That makes printer-side integration difficult to reproduce: a developer may be unable to test job upload, printer status changes, or completion when needed. The mock server provides a local, repeatable printer endpoint for development and integration testing.

It simulates configured Prusa printer profiles and accepts PrusaLink-style HTTP requests from the backend. It lets the team exercise the backend-to-printer boundary without requiring a physical printer.

## Responsibility boundary

The backend owns users, job records, the print queue, and dispatch decisions. The mock server represents printer-side behaviour: it accepts a file, validates it against the selected printer profile, simulates the print, and reports printer status. The frontend displays the backend's view of the job. The mock server does not own users or the queue.

## Components

| Component | Role |
| --- | --- |
| `mockserver/app/main.py` | Creates the FastAPI app, starts and stops printer workers, and registers the PrusaLink, operator-control, health, and monitor routes. |
| `mockserver/app/prusalink.py` | Implements the PrusaLink-style API used by the backend, including Digest authentication, status and job reads, file upload/start, pause, resume, and stop. |
| `mockserver/app/sdk_worker.py` | Coordinates a printer instance, G-code validation, simulator state, temperatures and filament accounting. It also contains the legacy Prusa Connect SDK worker flow; the Docker demo backend connects through the PrusaLink routes. |
| `mockserver/app/simulator.py` | Advances simulated printer state, temperatures, progress, active tool, and completion. |
| `mockserver/app/monitor.py` | Serves the live `/monitor` page and records backend actions and status polling for inspection. |
| `mockserver/config/printers.yaml` | Defines the enabled synthetic XL and CORE One instances, toolheads, spool values, profiles, storage paths, and per-printer simulation speeds. |
| `mockserver/tests/` | Tests simulator behavior, PrusaLink routes/authentication, transport/configuration, and G-code validation. |

## Request and status flow

```text
User submits job
      |
      v
Backend queue selects a printer and uploads G-code with Print-After-Upload
      |
      v
Mock PrusaLink endpoint receives the request and validates the file
      |
      v
Simulator preheats, prints, and reaches FINISHED (or a stopped/attention state)
      |
      v
Backend polls printer status and updates its job record
      |
      v
Frontend reflects the backend's updated job state
```

The simulator tracks an internal `PREHEATING` phase, then `PRINTING`, and finally `FINISHED`. Its PrusaLink status endpoint exposes printer state, temperatures, and an active job's progress and timing for backend polling.

## Simulated behavior

- Print progress and remaining/elapsed time based on the G-code estimated duration.
- Nozzle and bed temperature ramping; per-tool temperatures and active tool selection.
- Pause, resume, and stop through the PrusaLink job endpoints.
- Filament usage deducted from the configured spool when a print completes.
- Chamber temperature only for a printer configured with `chamber_supported: true` (the CORE One profile).
- G-code validation against the printer's configured profile; invalid uploads move the mock printer to `ATTENTION` rather than starting a print.

The configured XL has five toolheads; the CORE One has one high-flow toolhead and chamber support. These are simulated profiles and synthetic serials, credentials, and spool values.

## Configuration and timing

`mockserver/config/printers.yaml` defines each printer's ID, model/profile, token, storage directory, toolheads and spool contents, chamber support, and `simulation_speed`. Each approved profile maps G-code metadata to validation rules and command safety limits.

`MOCK_SIMULATION_SPEED` is an optional environment override applied to every configured printer at startup. A value of `1` advances simulation at wall-clock speed; higher values accelerate it. The G-code's estimated print duration remains the simulated print duration: for example, a 10-minute estimated print at speed `60` takes about 10 seconds of wall time after preheating. Preheating is simulated separately and does not advance print progress. The base YAML currently sets speed `120` for the XL and `60` for the CORE One; the demo overlay can override both.

## Run the local stack

From the repository root, start the UI, backend, mock server, and disposable demo database:

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build
```

This demo stack uses fake authentication and a local throwaway Postgres database. It does not require the backend's Supabase configuration. Open:

| URL | Purpose |
| --- | --- |
| http://localhost:5173 | Frontend demo |
| http://localhost:8000/docs | Backend API documentation |
| http://localhost:8080/monitor | Live mock printer status and received backend actions |

To stop the stack, use `Ctrl+C`, then run:

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml down
```

To run mock-server automated tests inside the running service:

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml exec mockserver pytest -q
```

Relevant tests include `mockserver/tests/test_simulator.py` for toolheads, completion, and filament use; `test_prusalink.py` for authentication, status, upload, job controls, and monitor; `test_validator.py` for G-code validation; `test_transport.py` for legacy transport constraints; and `test_queue_demo_config.py` for speed override/configuration and the demo G-code fixture. These describe tested behavior; this manual does not claim a test run.

## Demo scenario

1. Start the demo stack and submit a valid G-code job in the frontend.
2. The backend records the job in its queue and dispatches it to an available configured printer.
3. The backend uploads the G-code to the mock printer with `Print-After-Upload`; the mock validates it and begins the simulated print if valid.
4. Watch `/monitor` for printer state, progress, temperature, and the upload action. The backend polls status and updates its job record, which the frontend then displays.
5. At 100% progress, the mock reports `FINISHED`; the backend can mark the job complete.

The demo accounts and job availability depend on the disposable demo seed. The mock server itself does not create queue jobs.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Progress is much faster or slower than expected | Check `MOCK_SIMULATION_SPEED` and the per-printer `simulation_speed` values in `printers.yaml`. Speed changes wall-clock duration; it does not alter the G-code estimated print duration. |
| Mock server is unreachable | Confirm the mock service is running and that the backend uses the Compose service URL `http://mockserver:8080`. From the host, use port `8080`. |
| UI, API, or monitor does not load | Check that the Compose services are running; inspect logs with `docker compose -f docker-compose.yml -f docker-compose.demo.yml logs mockserver backend frontend`. |
| No jobs are visible | Confirm a job was submitted and that the backend has a configured printer available. The mock only receives work dispatched by the backend; it does not create jobs or queue entries. |

## Scope and limitations

The mock is intended for development and integration testing. It reproduces selected printer-side API and state behavior, but a simulation cannot represent every physical printer behavior, firmware response, hardware fault, or timing variation. Physical printer acceptance testing is still needed for behavior that depends on real hardware.
