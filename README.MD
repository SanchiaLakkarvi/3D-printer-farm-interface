# 3D Printer Farm Interface

A web-based 3D printer farm management system designed to provide a central interface for managing users, print jobs, queues, and multiple Prusa 3D printers.

> **Project status:** Backend MVP in progress (FastAPI + Supabase). No frontend yet — use the API docs UI to exercise Auth/RBAC.

---

## Getting started (local)

The implemented application lives in `backend/`. Docker is the preferred way to run it against the team Supabase project.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Access to the team Supabase project (URL, anon key, service-role key, DB password)

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` (never commit this file):

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Prefer the Supabase **Session pooler** URI (IPv4). Prefix with `postgresql+psycopg://`. Direct `db.*.supabase.co` is IPv6-only and often fails inside Docker Desktop on macOS. Pooler username is `postgres.<project-ref>`. |
| `AUTH_ADAPTER` | `supabase` for real Auth |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Server-only; from Supabase project settings |
| `SEED_*_PASSWORD` | Distinct non-empty passwords for demo Admin + Farmers |

Full variable list and Auth details: [`backend/README.md`](backend/README.md).

### 2. Start the API

From the **repository root**:

```bash
docker compose up --build
```

Detached:

```bash
docker compose up --build -d
```

Compose loads `backend/.env` and starts the FastAPI container on port 8000. Postgres and Auth come from Supabase (no local database container). Migrations are **not** applied on boot against the shared DB.

### 3. Open the API

| URL | Purpose |
|---|---|
| http://localhost:8000/health | Health check |
| http://localhost:8000/docs | Swagger UI (try endpoints) |
| http://localhost:8000/redoc | ReDoc |

There is no app UI at `/` — that path returns 404 by design.

### 4. Stop

```bash
docker compose down
```

### Without Docker

See [`backend/README.md`](backend/README.md) for venv, `uvicorn`, Alembic, tests, and Auth endpoint reference.

---

## 1. Project Overview

The goal of this project is to develop a university-wide 3D printer farm management platform, similar in purpose to an existing university printing portal while providing functionality that is currently missing from Prusa Connect.

The platform will provide a central place where students and staff can:

- Log in to the system
- Upload pre-sliced G-code files
- Validate uploaded G-code
- Select a compatible printer
- Submit jobs to a printer or queue
- Track printing progress and status
- Receive notifications about their jobs
- Pay personally or charge an approved unit code
- Collect completed prints after a printer-farm operator has removed them

The system is intended to reduce the manual administration required to manage users, printers, print queues, usage, and charging.

The project will use **Prusa printers** and will integrate with the available Prusa printer/API ecosystem. The exact integration approach will be confirmed during development after the team investigates the available Prusa Connect API and printer SDK.

---

## 2. Problem Statement

Prusa Connect provides useful functionality for controlling individual printers, but it does not provide everything required for a university-wide printer farm.

The client identified several limitations with the existing approach:

- Users must be manually invited to individual printers.
- Managing large numbers of students across multiple printers is impractical.
- There is no central farm-wide queue.
- Usage and billing tracking is limited.
- Detailed printer error information is limited.
- Unit-based charging and student limits are not supported in the required way.
- University-wide user management is not available.
- Printer material, colour, and estimated remaining filament are not clearly managed across the farm.

This project aims to provide an additional management layer over Prusa Connect or the relevant printer APIs.

---

## 3. Project Goals

The main goals of the project are to:

1. Provide a central interface for the university's 3D printer farm.
2. Allow students and staff to submit print jobs without requiring direct access to individual printers.
3. Validate G-code before a job is submitted to a printer.
4. Manage print jobs across multiple printers.
5. Provide a central print queue.
6. Track printer and job status.
7. Notify users and printer-farm operators when important events occur.
8. Support a workflow for completed-print removal and collection.
9. Provide basic pricing and usage tracking.
10. Provide administrators with useful reports and statistics.
11. Reduce manual administration for the printer-farm operators.

---

## 4. Intended Users

The system will have three primary roles.

### Student / Staff User

Users will be able to:

- Log in
- Upload G-code
- View and select compatible printers
- Submit print jobs
- View their job status
- Receive notifications
- Choose personal payment or an approved unit code where applicable
- Cancel eligible jobs
- Receive collection notifications

Initially, students and staff can use the same general interface. Differences may mainly relate to billing and unit charging.

### Farmer / Printer Operator

The printer-farm operator will be able to:

- View printer statuses
- View queued, active, completed, and failed jobs
- Respond to printer errors
- Record maintenance or interventions
- Remove completed prints
- Mark prints as ready for collection
- Confirm that a printer is clear
- Allow the next queued job to begin

A key part of the workflow is that the next queued job should not start until the completed physical print has been removed.

### Administrator

Administrators will have full system access and will be able to:

- Manage users
- Manage printers
- Manage unit codes
- Manage permissions
- View all print jobs
- Approve restricted jobs
- View reports
- View usage, cost, and material statistics
- Perform farmer/operator actions

---

## 5. Minimum Viable Product (MVP)

The client identified the following as the highest-priority functionality:

- Login system
- Multiple access levels
- File upload
- G-code validation
- Printer selection
- Print queue
- Sending files to a printer
- Printer status tracking
- User and farmer notifications
- Farmer collection workflow
- Basic pricing and usage tracking
- Administrator reports

These features form the initial scope of the project.

---

## 6. Core User Workflow

The intended print workflow is:

```text
User Login
    |
    v
Upload G-code
    |
    v
Validate G-code
    |
    v
Calculate Print Information
    |
    +--> Estimated Print Time
    +--> Estimated Filament Usage
    +--> Estimated Weight
    +--> Estimated Price
    |
    v
Select Compatible Printer
    |
    v
Select Payment / Unit Code
    |
    v
Submit Job
    |
    v
Print Queue
    |
    v
Printer Available
    |
    v
Send G-code to Printer
    |
    v
Printing
    |
    +--> Paused
    +--> Error
    +--> Failed
    |
    v
Print Completed
    |
    v
Waiting for Physical Removal
    |
    v
Farmer Removes Print
    |
    v
Ready for Collection
    |
    v
User Collects Print
```

The temporary G-code file should be deleted once the job has successfully completed, been removed, and no longer requires retrying. If a print fails, the file may be retained temporarily so that the operator or administrator can restart the job without requiring the user to upload it again.

---

## 7. G-code Validation

The initial MVP will support standard, human-readable G-code files generated by PrusaSlicer.

The system is expected to inspect configuration information stored near the end of a PrusaSlicer G-code file.

The validation process may check:

- Printer model
- Printer bed dimensions and shape
- Material type
- Nozzle / extruder configuration
- Printer profile
- Temperature settings
- Infill settings
- Layer and extrusion settings
- Estimated print duration
- Estimated filament usage
- Filament length
- Filament density
- Estimated filament weight

The client is comfortable with most slicer settings being locked to an approved standard configuration for the MVP.

A key requirement is to prevent a user from submitting G-code prepared for an incompatible printer model.

The client will provide:

- An approved PrusaSlicer configuration
- A sample G-code file
- Guidance about the exact validation settings

---

## 8. Printer Management

Users should be able to see information about available printers, including:

- Printer model
- Current status
- Material
- Filament colour
- Estimated remaining filament
- Queue length
- Availability
- Camera availability where applicable

The initial implementation can treat each printer as having one active material or toolhead, even where the physical printer supports multiple toolheads.

Supported printer/job-related states may include:

```text
Available
Queued
Uploading
Printing
Paused
Error
Completed
Waiting for Removal
Ready for Collection
Offline
Under Maintenance
```

---

## 9. Print Queue

The system will manage jobs across multiple printers.

The initial queue approach is:

> **First Come, First Served**

Future queue rules may include:

- Priority for users with lower resource usage
- Paid urgent jobs
- Short-job queues
- Administrator prioritisation of unit-related jobs

For the MVP, files should remain temporarily stored while waiting in the queue and should only be sent to the printer shortly before they are required.

This avoids filling printer storage with large numbers of queued files.

---

## 10. Notifications

The system should support notifications for important job and printer events.

### Main User Notifications

At minimum:

- Print started
- Print completed
- Print ready for collection

Additional notifications may include:

- Print paused
- Printer error
- Print failed
- Print restarted
- Print cancelled
- Approval required
- Approval granted
- Approval rejected

### Farmer Notifications

Operators should be notified when:

- A print finishes
- A printer pauses
- A printer runs out of filament
- A printer error requires physical intervention
- A completed print needs removal

The implementation is expected to support both:

- Real-time in-application notifications
- Email notifications

The exact messaging/notification infrastructure will be finalised during technical design.

---

## 11. Pricing and Charging

The platform should primarily calculate charges based on printing time rather than material weight.

The client suggested a pricing model where:

- The first hour has a higher flat charge.
- Following hours have a lower hourly charge.
- Very long jobs may have an increasing charge after a threshold such as 24 hours.

Exact prices have not yet been finalised.

Jobs may require approval if they exceed limits such as:

- More than 24 hours
- More than approximately 250 g of filament
- More than a specified percentage of a filament roll
- More filament than the estimated amount remaining
- A user's spending limit
- A unit's spending limit

The exact thresholds and cancellation/refund rules still need to be confirmed.

---

## 12. Payment and Unit Charging

Users should eventually be able to choose between:

- Personal payment
- Charging an authorised unit code

The system should not store card details.

For the initial prototype, a simulated payment process may be sufficient.

Administrators or unit coordinators should be able to:

- Upload a student list
- Assign students to a unit
- Set a unit spending limit
- Track individual usage
- Export usage reports

---

## 13. Filament Tracking

The system should estimate remaining filament by:

```text
New Spool
    |
    v
Record Starting Amount
    |
    v
Read Required Filament from G-code
    |
    v
Print Completed
    |
    v
Subtract Used Filament
    |
    v
Estimated Remaining Filament
```

This will only be an estimate because a printer may be used outside the platform.

The system may warn or block a job if the estimated filament requirement is greater than the available amount.

Administrators may be able to override the warning.

---

## 14. Reporting and Analytics

The administrator dashboard should eventually provide reports based on:

- Student
- Staff member
- Unit code
- Printer
- Material
- Colour
- Date range
- Semester
- Academic year
- Print duration
- Filament usage
- Cost
- Job status
- Failure rate
- Maintenance history

Important statistics include:

- Total print jobs
- Successful jobs
- Failed jobs
- Cancelled jobs
- Total printing hours
- Total filament used
- Filament used by material
- Filament used by colour
- Filament used by printer
- Usage per student
- Usage per unit
- Charges/revenue
- Average job duration
- Printer utilisation
- Number of unique users
- Maintenance frequency

Reports should eventually be exportable to formats such as CSV or Excel.

---

## 15. Data and Privacy

The system should minimise the amount of stored data.

Permanent records may include:

- User identity
- Student/staff number
- Unit membership
- Job metadata
- Printer used
- Print duration
- Filament usage
- Charges
- Job status
- Timestamps
- Reports and statistics

Complete G-code files should only be stored temporarily.

The user remains responsible for keeping their original STL or G-code file.

---

## 16. Prusa Integration

The project will use Prusa printers.

The team will investigate the available:

- Prusa Connect API
- Printer SDK/API capabilities
- Printer status information
- File upload functionality
- Print control functionality
- Camera functionality where available

A dedicated integration layer should be considered so that the rest of the application does not depend directly on Prusa-specific implementation details.

Conceptually:

```text
Application
     |
     v
Printer Integration Layer
     |
     v
Prusa Connect / Printer API
     |
     v
Prusa Printer
```

The exact API and integration approach will be confirmed after the team receives read-only access to the existing Prusa Connect environment and investigates the available API/SDK.

---

## 17. Real-Time Events and Notifications

The project is expected to benefit from an event-driven approach for printer and job updates.

For example:

```text
Prusa Printer
     |
     v
Printer Integration
     |
     v
Job Status Change
     |
     v
Event
     |
     v
Message Queue
     |
     +------------------+
     |                  |
     v                  v
Database           Notification
Update                 Service
                         |
                  +------+------+
                  |             |
                  v             v
              WebSocket       Email
                  |             |
                  v             v
               User          Student /
               UI             Farmer
```

This is a proposed technical direction rather than a confirmed client requirement. The final implementation will be decided during technical design.

---

## 18. Camera Feature

Camera functionality is considered a **nice-to-have**, not an essential MVP feature.

Possible future functionality includes:

- Viewing the latest printer image
- Manual image refresh
- Capturing an image when a print completes
- Including a completed-print image in notifications
- Helping operators identify failed or "spaghetti" prints

Continuous camera polling should be avoided unless required.

---

## 19. Testing Approach

The client is comfortable with controlled testing using the real printers.

The team should avoid repeatedly producing physical objects during development.

Possible testing approaches include:

- Simulated printer statuses
- Mock printer API responses
- Uploading files without starting a print
- Modified G-code containing only start/end commands
- Low-temperature testing
- Homing or moving the printer head without extrusion
- One complete physical test near the end of development

A final end-to-end test may cover:

```text
Upload
  |
Validation
  |
Printer Selection
  |
Queue
  |
Send to Printer
  |
Start Print
  |
Notifications
  |
Completion
  |
Farmer Removal
  |
Collection Notification
```

---

## 20. Current Project Status

### Completed

- Initial client requirements meeting
- Initial MVP requirements identified
- User roles identified
- Main print workflow identified
- Main printer workflow identified
- Initial reporting requirements identified
- Prusa integration identified as a core technical area
- Backend foundation: FastAPI, Docker Compose, Supabase Postgres + Auth
- Email/password Auth with Student Sign-up, Sign-in, `/me`, and RBAC probes

### Not Yet Finalised / not built

- Frontend (Next.js planned; not in repo yet)
- Exact Prusa API/SDK integration approach
- Exact G-code validation rules
- Pricing values
- Cancellation/refund policy
- Approval thresholds
- Payment implementation
- Final queue rules beyond the agreed FCFS design
- Deployment/hosting environment beyond local Docker + Supabase

---

## 21. Immediate Next Steps

Before significant development begins, the team should:

1. Request read-only access to the existing Prusa Connect environment.
2. Obtain the sample G-code file from the client.
3. Obtain the approved PrusaSlicer configuration.
4. Confirm the required G-code validation settings.
5. Investigate the Prusa Connect API and printer SDK.
6. Define the final MVP scope.
7. Convert requirements into user stories.
8. Identify the main system entities and data requirements.
9. Design the initial print-job lifecycle.
10. Decide on the development technology stack.
11. Create initial UI wireframes.
12. Define the initial pricing model.
13. Decide how real-time events and notifications will be implemented.
14. Establish the team's Git/GitHub workflow.
15. Arrange fortnightly progress updates with the client.

---

## 22. Project Documentation

This README covers product requirements and how to run the current backend locally.

Technical references:

- Backend setup, Auth endpoints, migrations, tests: [`backend/README.md`](backend/README.md)
- Database schema notes: [`Docs/Guides/database_schema.md`](Docs/Guides/database_schema.md)
- Auth specification: [`Docs/specs/authentication.md`](Docs/specs/authentication.md)
- Agreed MVP / Assignment 1: [`Docs/Assignment1/Assignment1.md`](Docs/Assignment1/Assignment1.md)
- Client decisions: `Meeting Minutes/`

Additional documentation may include architecture diagrams, G-code validation specs, Prusa integration notes, UI designs, and deployment guides as those areas are implemented.

---

## 23. Client Resources

The client has agreed to provide:

- Read-only access to the existing Prusa Connect environment
- Access to the printer with a camera
- Sample G-code
- Approved PrusaSlicer configuration
- Guidance about validation settings
- Controlled printer access for testing

---

## 24. Communication

The client requested progress updates at least fortnightly.

Communication can take place through:

- In-person meetings
- Microsoft Teams
- Email
- Teams for urgent questions

---

## 25. Scope Direction

### MVP

The initial development focus should be:

```text
Authentication
     +
User Roles
     +
G-code Upload
     +
G-code Validation
     +
Printer Selection
     +
Queue
     +
Prusa Integration
     +
Printer Status
     +
Notifications
     +
Farmer Collection Workflow
     +
Basic Pricing
     +
Usage Tracking
     +
Admin Reports
```

### Future / Stretch Features

These can be considered after the core workflow is working:

- Web-based STL/3D model slicing
- Advanced queue prioritisation
- More accurate spool tracking
- Online payments
- Live/advanced camera functionality
- More advanced pricing
- Additional printer types
- Additional automation

---

## 26. Guiding Principle

The first goal is to build a reliable end-to-end workflow:

> **User submits a valid print → the system queues it → a compatible Prusa printer prints it → the system tracks the job → the farmer removes the print → the user is notified to collect it.**

Once this workflow is stable, additional functionality can be built around it.

---

## Reference

Requirements and scope in this README are based on the **3D Printer Farm Interface – Client Meeting Notes, 30 July 2026**.
