# Section 1: Problem Statement: What Are We Going to Build and Why?

## 1.1 Background and Current Problem

UWA Mechanical Engineering currently operates two web-connected 3D printers through PrusaConnect. The client’s initial vision is to develop a web-based system similar to print.uwa.edu.au and PrusaConnect, allowing students and staff to access a shared 3D printer farm, submit print files, select an appropriate printer, and monitor their print jobs. The system is initially intended to support the Prusa XL and Prusa CORE One printers available at UWA, while providing a foundation for future expansion of the printer farm.

The current PrusaConnect-based process does not scale effectively to a larger number of users. Print jobs are submitted directly to individual printers, and users must be invited separately to each printer before they can access it. This approach is manageable for a small number of users but becomes impractical when supporting approximately 50–200 students in a semester. The current system also lacks account-level history and centralised usage tracking.

The core problem is therefore the absence of a centralised and scalable web-based system for managing access to the printer farm, validating print jobs, assigning jobs to suitable printers, tracking print activity, and reducing the manual effort required to operate the service.

Current-state workflow:

User → Individual invitation to a specific printer → Direct submission to that printer → Printer access and jobs managed individually

## 1.2 Client Need and Project Value

The client wants students and staff to access the printer farm through a common system rather than being manually added to individual printers. The initial project brief proposed access through a UWA identity, but the refined requirements allow a simpler login mechanism for the initial system. The key requirement is to provide convenient user access while minimising printer-level administration. The client described this objective as “minimal admin interaction.”

The system is also expected to improve visibility of printer-farm usage. The client requires tracking of material used per print, lifetime usage by students or staff, usage by unit code, and long-term statistics by printer and material. Cost accounting is also part of the project requirement, although the final pricing values and staff billing arrangements have not yet been confirmed.

The primary users are students and staff who submit and track print jobs, Farmers who manage printers and completed jobs, and Administrators who require access to overall usage information and reports.
By centralising these activities, the proposed system will reduce repetitive administration, improve visibility of printer usage, and provide a more scalable approach to managing a growing printer farm.

## 1.3 Proposed System

The project will develop a web-based 3D Print Farm Management System that provides a central interface for submitting, validating, assigning, and tracking 3D printing jobs.

Proposed-state workflow:

Login → Upload G-code → Select Printer/Material → Validate → Submit/Queue → Print → Notify

Users will upload a standard pre-sliced G-code file and either select a specific printer or request any printer with the required material. The uploaded file will be validated against the target printer’s locked configuration, including relevant machine settings such as material, bed size, and printer profile. Files that do not match the required configuration will be rejected or flagged before being sent to a printer.

The default queue approach will be first come, first served. Users will be able to view basic job status and will receive notifications when a print starts, completes, or stops because of an error. The system will also record relevant print and usage information to support long-term monitoring and reporting.

## 1.4 Key MVP Deliverables

The key MVP deliverables are:

* A multi-level login system
* Upload of standard G-code print jobs
* Validation of uploaded G-code against the target printer’s locked configuration
* Assignment of jobs to an appropriate printer
* Aasic print-job tracking and status information
* Notifications for job start, completion, and error/stopped states.

The client confirmed that the minimum successful outcome for the semester is a system that supports multiple login levels, basic notifications, and the complete upload → validate → submit → notify workflow.

Online slicing, camera integration, and automatic remaining-filament tracking were discussed as possible extensions but are not required for the core MVP. Detailed MVP functionality and evidence of client agreement are presented in Section 2: Client Communication and MVP Agreement.

## 1.5 Scope and Major Constraints

The project scope is focused on delivering the core workflow required to submit and manage 3D printing jobs using the existing web-connected printer environment. The initial system will primarily support standard pre-sliced G-code files and will treat each print job as a single-toolhead job. Multi-material and multi-colour printing are outside the core MVP.
Uploaded G-code must be validated against the locked configuration of the selected printer. Relevant settings such as material, bed size, and printer profile will be checked, while filament colour will not be used as a validation condition because available colours may change.

Physical printer testing is constrained during development. The client has requested that routine testing use simplified G-code containing only start and end operations, without actual extrusion. A full physical print test will be performed near project completion with the client present.
Online slicing, camera integration, and automatic remaining-filament tracking are optional extensions rather than core MVP requirements. These features will only be considered if time permits after the core MVP functionality has been prioritised.


# Section 2: Client Communication and MVP Agreement

## 2.1 Client Information

**Project:** 3D Printer Farm Interface  
**Client:** Dr Christopher Lamb  

---

## 2.2 Client Communication Approach

### Communication Channels

The team and client agreed to use the following communication channels:

| Channel | Purpose |
|---|---|
| Email | Formal communication, requirement clarification, and sharing important project updates |
| Microsoft Teams | For meetings, urgent questions, and project discussions |
| In-person meetings | Requirement discussions and progress reviews when required |

The client requested progress updates at least **fortnightly**. Meetings may be held in person or through Microsoft Teams.

---

### Meeting Schedule

| Meeting Type | Frequency |
|---|---|
| Client progress meeting | Fortnightly |
| Requirement clarification | As required |
| MVP validation meetings | At major development milestones and on every client meeting |

---

### Project Documentation and Evidence

**Microsoft Teams Area/Channel:**  

**Meeting Notes Link:**  
<https://uniwa.sharepoint.com/:b:/r/teams/CITS5206-InformationTechnologyCapstoneProjectSEM-22026-Group16/Shared%20Documents/3D%20Printer%20Farm%20Interface%20Client%20Meeting%20Notes.pdf?d=w90be0eb5874f49eda8602f4df0e46461&csf=1&web=1&e=0fid0E>

**Github Repository Link:**
<https://github.com/SanchiaLakkarvi/3D-printer-farm-interface>

The initial client requirements meeting was conducted on:

**Date:** 30 July 2026  
**Meeting Type:** Initial client requirements meeting  
**Project:** 3D Printer Farm Interface  

The meeting covered the project objectives, the limitations of the current system, the MVP scope, technical flexibility, communication expectations, and immediate action items.

---

## 2.3 Summary of Initial Client Meeting

During the initial client meeting, the team discussed the requirements for a university-wide 3D printer farm management platform.

The client explained that managing printers through Prusa Connect is not suitable for the university environment because:

- Admin must currently be manually invited to individual printers.
- There is no centralised printer farm queue.
- Usage and billing tracking are limited.
- University-wide user management is not supported.
- Printer material, colour, and filament availability are difficult to manage.



The proposed system is intended to make the printing workflow simpler. It will allow students and staff to upload print files, select suitable printers, submit jobs, track progress, receive notifications, and collect completed prints.

---

## 2.4 Client Priorities

The client confirmed the following as the highest-priority requirements:

1. User login system
2. Multiple user access levels- Student/Staff, Farmer, Admin
3. File upload
4. G-code validation
5. Printer selection
6. Print queue management
7. Sending files to printers
8. Printer status tracking
9. User and farmer notifications
10. Farmer collection workflow
11. Basic pricing and usage tracking
12. Administrator reporting

These priorities form the core workflow for the first working version of the system.

---

## 2.5 Agreed Minimum Viable Product (MVP)

The following features were agreed with the client for the MVP.

### 1. User Authentication

The system will allow users to log in.

Required information:

- User email address
- Name
- Student/staff number

Either a custom authentication system or email-based passwordless login is acceptable.

---

### 2. User Roles and Permissions

The MVP will include three user roles:

### Student/Staff User

Users can:

- Upload print files
- Select printers
- Submit print jobs
- View job status
- Receive notifications



### Printer Farmer / Operator

Farmers can:

- View printer status
- Manage completed or failed jobs
- Remove completed prints
- Mark prints as ready for collection
- Respond to printer errors
- Record maintenance actions



### Administrator

Administrators can:

- Manage users and printers
- Manage permissions
- View all jobs
- Generate reports
- Monitor usage and costs


---

### 3. File Upload and Validation

The MVP will allow users to upload standard G-code files generated by PrusaSlicer.

The system will check the following information:

- Printer compatibility
- Material type
- Printer profile
- Temperature settings
- Estimated printing duration
- Filament usage

The client agreed that approved slicer configurations can be used initially to simplify validation.

---

### 4. Printer Selection and Queue Management

Users will be able to see:

- Printer model
- Current status
- Material
- Filament colour
- Remaining filament estimate
- Queue length
- Availability


Initially, the queue will use a first-come, first-served approach.

---

### 5. Printing Workflow

The agreed MVP workflow is as follows:

1. User logs in.
2. User uploads G-code.
3. System validates the file.
4. User selects a compatible printer.
5. Job enters the queue.
6. System sends the file to the printer.
7. System monitors printing progress.
8. Notifications are sent for important events.
9. Farmer removes completed prints.
10. User receives collection notification.


---

## 2.6 Features Outside the MVP

The following features were identified as non-essential for the initial MVP:

| Feature | Reason |
|---|---|
| Web-based STL slicing | Additional complexity; users can initially upload pre-sliced G-code |
| Advanced queue prioritisation | First-come-first-served is Decided initially |
| Real-time camera streaming | Considered unnecessary for the core workflow, can be added at the later stage |
| Full online payment integration | Prototype payment simulation is acceptable |
| Highly accurate filament tracking | Estimates are acceptable initially |

The client identified these features as possible extensions once the core workflow is complete.

---

## 2.7 Optional / Stretch Features

Possible future enhancements include:

- Camera monitoring of printers
- Automatic failed print detection
- Live print images in notifications
- Advanced queue optimisation
- Automated payment provider integration
- Advanced analytics dashboards

---

## 2.8 Acceptance Criteria

The MVP will be considered successful when it meets the following criteria:

| Requirement | Acceptance Criteria |
|---|---|
| Authentication | Users can securely log into the system |
| File upload | Users can upload valid G-code files |
| Validation | System detects incompatible printer settings |
| Printer selection | Users can select available compatible printers |
| Queue system | Jobs are managed correctly across printers |
| Notifications | Users and farmers receive status updates |
| Farmer workflow | Farmers can mark completed prints as collected |
| Reporting | Administrators can view the usage information |

---

## 2.9 Requirement Change Management

Any changes to requirements after the MVP agreement will follow this process:

1. Any requested change to the scope or requirements is documented in the dated meeting notes.
2. The team evaluates the impact on:
   - Development effort
   - Timeline
   - MVP scope
   - Existing functionality
3. A written summary is then emailed to the client for confirmation.
4. Client approval is required before implementation.
5. Approved changes are added to the updated requirements document and the team's backlog.

All email confirmations are retained in a dated change log.

---

## 2.10 Client Confirmation and Agreement Evidence

During the initial requirements meeting, the client reviewed and confirmed the team's interpretation of the requirements.

Evidence includes:

- Confirmed MVP priorities.
- Agreement on required user roles.
- Agreement on printer workflow.
- Agreement on communication frequency.
- Confirmation of future extension features.


---
# Section 3: Project Planning and Management

## 3.1 Team Structure and Responsibilities

The project is being completed by a team of five students. Primary responsibilities have been allocated according to each member’s interests and technical strengths, while all members will contribute to planning, development, testing and documentation.

| Team member | Primary project responsibility | Assignment 1 responsibility |
| --- | --- | --- |
| Sanchia Recson Lakkarvi | Frontend development, user-interface design and project-planning coordination | Project Planning and Management |
| Nuwanga | Backend development and implementation of the system’s internal and external interfaces | Problem Statement and Gantt chart |
| Sahil Pankajbhai Patel | Requirements analysis, MVP definition and testing coordination | Client Communication and MVP Agreement |
| Su-Yeon Yang (Jesse) | Database design, data management and GitHub Project-board maintenance | Risk and Technology Assessments |
| Han Nguyen | Supporting research, documentation, meeting-minute coordination and development assistance | Executive Summary and research into existing systems and resources |

These responsibilities establish accountability without preventing collaboration. Authentication, available Prusa-interface integration, queue management and end-to-end testing affect several components and will therefore be completed collaboratively. The allocation will be reviewed during weekly meetings and adjusted if workloads become uneven or technical requirements change. Changes to ownership will be recorded in the meeting minutes and GitHub Project board.

## 3.2 Project Management Approach

The team will use an adapted Agile approach with weekly iterations. This is appropriate because access to Prusa Connect, the precise interfaces available for integration and the format of the client’s sample G-code still require investigation. Weekly iterations allow the team to test assumptions, obtain feedback and adjust the implementation without delaying the entire project.

GitHub Projects will be the central task-management tool. GitHub Projects integrates issues and pull requests into adaptable board, table and roadmap views for planning and tracking work [1]. Each work item will be represented by an issue or task with an owner, priority, due date and status. The workflow is:

1. **Backlog** — identified work that has not yet been selected.
2. **Ready** — sufficiently defined and prioritised for development.
3. **In Progress** — actively being completed by the assignee.
4. **In Review** — implementation or documentation awaiting peer review.
5. **Testing** — reviewed work undergoing verification against its acceptance criteria.
6. **Done** — work that satisfies the Definition of Done in Section 3.8.

At the beginning of each iteration, the team will select the highest-priority ready items and confirm their acceptance criteria. Progress, blockers and workload will be reviewed at the weekly meeting. Incomplete work will be re-estimated and rescheduled rather than marked complete.

- **Project board:** [3D Printer Farm Project Board](https://github.com/users/SanchiaLakkarvi/projects/1)
- **GitHub repository:** [3D Printer Farm Interface](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface)

## 3.3 Communication, Meetings and Access

Microsoft Teams will be used for team discussions, meeting invitations, shared documents and communication with the facilitator. GitHub will be used for source code, issues, technical documentation and evidence of development activity.

The team will meet internally each week to review completed work, discuss blockers and allocate the next tasks. Additional technical sessions may be arranged for integration and testing. Client progress meetings are planned approximately fortnightly, subject to availability, and the team will attend scheduled facilitator meetings.

Each formal meeting will have an agenda and minutes recording the date, duration, attendees, discussion points, decisions, actions, owners and due dates. Han will coordinate meeting minutes, while the chair of each meeting will check their accuracy. Important decisions made through informal messages will be transferred to the relevant minutes or GitHub issue.

- **Teams group chat:** [CITS5206 Capstone Project](https://teams.microsoft.com/l/chat/19:6ac1f08bbe3842ac9482806611f8d65c@thread.v2/conversations?context=%7B%22contextType%22%3A%22chat%22%7D)
- **Teams channel:** [Group 16 — CITS5206](https://teams.microsoft.com/l/channel/19%3ArHO415s3NliOh0Xvy5c56TTmpTiefwlMZl0XpurCo3E1%40thread.tacv2/Group%2016?groupId=4259f431-6994-4e09-90b6-cac70831356a&tenantId=05894af0-cb28-46d8-8716-74cdb46e2226&ngc=true)
- **Meeting minutes:** [Meeting Minutes folder](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/main/Meeting%20Minutes)
- **Gantt chart:** [3D Printer Farm Gantt Chart](https://uniwa-my.sharepoint.com/:x:/r/personal/24684008_student_uwa_edu_au/Documents/Microsoft%20Teams%20Chat%20Files/3D%20Printer%20Farm%20Gantt%20Draft%20.xlsx?d=w051a67770a5b42218d517edcfc95b31f&csf=1&web=1&e=O2KhUP)

Before submission, the team will test these links using the facilitator’s account or a non-owner account. The facilitator will be granted access to the repository, Project board, Teams channel, meeting minutes and Gantt chart. An accessible copy of the Gantt chart will also be committed to the GitHub repository so that project evidence is not dependent on a personal SharePoint link.

## 3.4 Initial Product Backlog

The backlog aligns with the confirmed MVP described in Sections 1 and 2: authentication and role-based access control, G-code submission and validation, compatible-printer selection, queue management, job tracking, notifications, the farmer collection workflow and basic usage reporting. Items that depend on unconfirmed pricing, approval or integration rules are explicitly recorded as open decisions rather than guaranteed MVP functionality.

| Priority | Backlog item | Expected outcome |
| --- | --- | --- |
| **Must have** | Email-based authentication and role-based access control | Approved users can sign in, and student/staff, farmer and administrator permissions are separated. |
| **Must have** | Printer list | Users can view available printers, status, supported material, colour and availability. |
| **Must have** | Pre-sliced G-code upload | Users can upload an accepted, human-readable G-code file. |
| **Must have** | G-code validation | The system checks the file against the approved printer and slicing constraints available to the team. |
| **Must have** | Print-duration and filament-use estimation | Before submission, the system displays the estimated duration and filament required using information available in the G-code or approved parsing rules. |
| **Must have** | Compatible-printer selection | A user can select a compatible printer or printer group. |
| **Must have** | Compatibility-aware queue management | Jobs follow first-come, first-served ordering within a compatible printer queue or printer group. An incompatible job does not block another compatible job from using an available printer. |
| **Must have** | Job tracking | Users can view the current status and relevant progress information for their jobs. |
| **Must have** | Farmer collection workflow | Farmers can record printing, completion, removal and readiness for collection. |
| **Must have** | Basic notifications | Relevant users receive email notifications for major status changes, including completion or readiness for collection. |
| **Must have** | Administration and basic usage reporting | Administrators can manage relevant users, printers and jobs and view basic usage information. |
| **Must have** | Printer integration layer | The application communicates through the available Prusa interfaces where access permits, while remaining testable through an internal mock printer service. |
| **Open decision / Should have** | Indicative price estimation | An indicative cost is displayed only if the client confirms pricing inputs and staff/student billing rules. |
| **Open decision / Should have** | Approval rules and limits | Approval is applied only if the client confirms thresholds for duration, filament, cost or configuration. |
| **Future / Stretch** | Automatic remaining-filament tracking | The system estimates remaining spool quantity from recorded spool data, job consumption and manual corrections. This is distinct from estimating the filament required by an uploaded job. |
| **Could have** | Expanded analytics | Detailed printer, user, teaching-unit and cost reports are available. |
| **Future** | STL upload and online slicing | Users can upload STL files and slice them through the web platform. |
| **Future** | Camera monitoring | Authorised users can view printer images or a live camera feed. |
| **Future** | Real payment processing | Personal payments can be processed through an approved external payment service. |

### Queue Rule

Jobs will follow first-come, first-served ordering within a compatible printer queue or printer group. A job that is incompatible with an available printer will not prevent another compatible job from using that printer.

For example, if an earlier job can run only on a Prusa XL while a later job is compatible with an available Prusa CORE One, the later compatible job may use the CORE One without changing the earlier job’s relative position in the XL-compatible queue.

## 3.5 Initial User Stories

The following user stories describe the main outcomes expected from the MVP and its recorded open decisions:

1. As a student or staff member, I want to sign in using my email so that I can securely access the printing service.
2. As a user, I want to upload a pre-sliced G-code file so that I can submit a print without manually accessing Prusa Connect.
3. As a user, I want the system to validate my file so that incompatible or unsafe settings are identified before printing.
4. As a user, I want to view the estimated print duration, filament required and, where pricing rules are available, the indicative cost before submitting the job.
5. As a user, I want to select a compatible printer or printer group so that my job enters an appropriate compatibility-aware queue.
6. As a user, I want to track my job status so that I know whether it is submitted, queued, printing, completed, removed or ready for collection. An approval status will be included only if approval rules are confirmed.
7. As a farmer, I want to update printing, completion, removal and collection statuses so that users and administrators have accurate job information.
8. **Open decision:** As an administrator, I want to review jobs exceeding confirmed limits so that long, costly or material-intensive jobs can be controlled. This story will enter the committed scope only if the client confirms the approval thresholds and process.
9. As an administrator, I want to view basic usage information so that printer utilisation and filament use can be monitored and reported.
10. As a developer/tester, I want a mock printer service that simulates printer states and responses so that the system can be tested when physical printers are unavailable.

Acceptance criteria will be added to the relevant GitHub issues before development begins. User Story 4 must be accepted even when no cost is displayed if pricing rules remain unavailable; in that case, duration and filament-use estimates remain mandatory. User Story 8 must not be treated as a Must-have item until the client’s decision is documented in meeting minutes.

## 3.6 Milestones and Schedule

| Dates | Main activities | Expected milestone |
| --- | --- | --- |
| **27 July–16 August 2026** | Client consultation, problem definition, MVP agreement, risk assessment and initial planning | Project scope and Assignment 1 completed |
| **17–30 August 2026** | Architecture, database schema, interface wireframes, investigation of available Prusa interfaces and development-environment setup | Technical foundation reviewed by the team |
| **31 August–13 September 2026** | Authentication, roles, printer list, G-code upload, validation, duration and filament-use estimation | First usable vertical prototype |
| **14–27 September 2026** | Compatible-printer selection, compatibility-aware queue management and job tracking; investigate price and approval rules if confirmed | Core job-submission workflow completed |
| **28 September–11 October 2026** | Farmer collection workflow, notifications, administration, basic reporting and integration | Feature-complete MVP |
| **12 October–1 November 2026** | Unit, integration, end-to-end and usability testing; available physical-printer testing; client feedback; defect correction and documentation | Validated system and project handover |

The detailed Gantt chart records task owners, dependencies, start and end dates and milestones. If unit deadlines or client availability change, the chart and corresponding GitHub issues will be updated together.

## 3.7 Git and Pull-Request Workflow

Development will take place in the shared GitHub repository. The `main` branch will contain stable, reviewed work. Members will create a separate branch for each feature, defect or documentation task, using names such as `feature/gcode-upload`, `fix/queue-status` or `docs/setup-guide`.

When work is ready, the contributor will open a pull request explaining the change, testing completed and related issue. GitHub issues, pull requests and Projects provide linked mechanisms for assigning responsibility, discussing work and tracking implementation progress [1].

At least one other team member will review each pull request before merge. Review will consider functionality, readability, security, tests and compatibility with the existing system. Significant work will not be merged directly into `main`. The contributor will resolve merge conflicts in consultation with the owner of the affected component. Commits, reviews and pull requests will provide evidence of individual contribution.

## 3.8 Testing and Definition of Done

Mocked and simulated printer behaviour is the team’s testing approach; it is not presented as a client-approved requirement unless that approval is later documented in meeting minutes. The team will build a mock printer service that can reproduce relevant printer states, successful responses and failure conditions when physical printers or integration access are unavailable. Testing against a physical printer and the available Prusa interfaces will be performed when access is provided.

Testing will include unit tests for individual functions, integration tests across the frontend, backend, database and printer-integration boundary, end-to-end tests for the main user workflows, and manual usability testing for students/staff, farmers and administrators. Sahil will coordinate the test plan and testing evidence, while feature owners remain responsible for tests relating to their work.

A backlog item is **Done** only when it satisfies the team’s agreed quality criteria. Specifically:

1. Its agreed acceptance criteria have been met.
2. The work has been committed to the correct branch.
3. Relevant tests have passed and evidence is recorded.
4. Invalid inputs and important error cases have been considered.
5. Another team member has reviewed the pull request.
6. The change has been merged without breaking existing functionality.
7. Related technical and user documentation has been updated.
8. The GitHub issue and Project-board status have been updated.
9. The feature has been demonstrated to the team and, where appropriate, the client.

## 3.9 Contribution and Project-Control Tracking

Individual contributions will be recorded through assigned issues, commits, pull requests, reviews, meeting attendance, minutes, design files, testing evidence and documentation. Each member must provide regular progress updates and raise blockers early.

Jesse will maintain the GitHub Project board and check that issues have owners, priorities, dates and correct statuses. Han will coordinate meeting minutes and action records. Sahil will coordinate testing activities and the test-evidence summary. Sanchia will coordinate the overall planning documents and verify that the schedule, repository evidence and Section 3 remain consistent.

The team will review workload distribution weekly, and collaborative issues will record each participant’s contribution for transparent peer evaluation.

## 3.10 Managing Delays and Requirement Changes

Potential delays will be raised during weekly meetings or through Teams as soon as they are identified. The team will assess the affected item’s priority, dependencies and remaining effort and may divide, reassign or reschedule it. The agreed MVP will take priority over optional work.

If access to Prusa Connect, a physical printer or another expected integration route is delayed, development and testing will continue through the mock printer service and an abstraction around the available Prusa interfaces. The wording “Prusa Connect API” will not be used as a guaranteed dependency until the team confirms the specific interface and receives the required access. Prusa’s documentation distinguishes the cloud-based Prusa Connect service from locally accessed PrusaLink [2]. Therefore, the final technical route remains subject to access and investigation.

If the client is temporarily unavailable, questions and assumptions will be grouped, documented and sent for confirmation. New requirements will first be recorded in a GitHub issue or change log with their purpose, priority, effort and schedule effect. A material change to the MVP will require client confirmation and supporting meeting minutes.

If time becomes limited, online STL slicing, live-camera integration, automatic remaining-filament tracking, real payment processing and expanded analytics will remain outside the MVP. Unconfirmed price estimation and approval rules will also remain open decisions.

This protects the guaranteed core workflow: sign in; upload and validate G-code; estimate print duration and filament use; select a compatible printer or printer group; submit to a compatibility-aware queue; track the job; notify the user of major status changes; support the farmer completion and collection process; and provide basic usage reporting.

## References

[1] GitHub, “About Projects,” *GitHub Docs*. [Online]. Available: https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects. [Accessed: Aug. 15, 2026].

[2] Prusa Research, “Prusa Connect and PrusaLink explained,” *Prusa Knowledge Base*. [Online]. Available: https://help.prusa3d.com/article/prusa-connect-and-prusalink-explained_302608. [Accessed: Aug. 15, 2026].
