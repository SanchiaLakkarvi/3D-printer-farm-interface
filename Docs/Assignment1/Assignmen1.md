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

During the Secong meeting on August 11, the client reviewed and confirmed the team's interpretation of the requirements.

Evidence includes:

- Confirmed MVP priorities.
- Agreement on required user roles.
- Agreement on printer workflow.
- Agreement on communication frequency.
- Confirmation of future extension features.

below is the attached email which confirmed the client is statisfied with the MVP draft and all of the requirements that we finalised.

![Email](email.png)

---
# Section 3: Project Planning and Management

## 3.1 Team Structure and Responsibilities

The project is being completed by a team of five students. Responsibilities have been allocated according to each member’s interests and technical strengths while still allowing everyone to participate in planning, development, testing and documentation. The initial allocation is shown below.

| Team member             | Primary project responsibility                                                               | Assignment 1 responsibility                                        |
| ----------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Sanchia Recson Lakkarvi | Frontend development, user interface design and coordination of project-planning activities  | Project Planning and Management                                    |
| Nuwanga                 | Backend development and API implementation                                                   | Problem Statement and Gantt chart                                  |
| Sahil Pankajbhai Patel  | Requirements analysis, MVP definition and supporting API research                            | Client Communication and MVP Agreement                             |
| Su-Yeon Yang (Jesse)    | Database design, data management and task tracking                                           | Risk and Technology Assessments                                    |
| Han Nguyen              | Supporting research, documentation and development assistance based on the team’s priorities | Executive Summary and research into existing systems and resources |

These responsibilities identify the main area of ownership for each member but do not prevent collaboration. Tasks that affect several parts of the system, such as authentication, printer integration, queue management and end-to-end testing, will be completed collaboratively. The team will review the allocation as the project progresses and redistribute tasks if workloads become uneven or new technical requirements arise.

Detailed development responsibilities may be adjusted after the initial requirements and technical architecture have been reviewed. Any changes will be recorded in the meeting minutes and updated on the GitHub Projects board.

---

## 3.2 Project Management Approach

The team will use an adapted Agile approach with short weekly iterations. This approach was selected because some technical details, particularly access to Prusa Connect, the available printer interface and the format of the client’s sample G-code, still require investigation. Weekly iterations will allow the team to test assumptions early, receive feedback and adjust the implementation without delaying the entire project.

GitHub Projects will be used as the central task-management tool. Each work item will be created as an issue or task and assigned an owner, priority, due date and status. The project board will contain the following stages:

1. Backlog
2. Ready
3. In Progress
4. In Review
5. Testing
6. Done

At the beginning of each weekly iteration, the team will select the highest-priority items from the backlog and confirm the expected outcome of each task. Progress will be reviewed during the weekly team meeting. Incomplete work will be discussed, re-estimated and moved into the next iteration where appropriate.

**Project board:** [3D Printer Farm Project Board](https://github.com/users/SanchiaLakkarvi/projects/1)

**GitHub repository:** [3D Printer Farm Interface](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface)

---

## 3.3 Communication and Meeting Arrangements

Microsoft Teams will be used for team discussions, meeting invitations, shared documents and communication with the facilitator. GitHub will be used for source code, issues, technical documentation and evidence of development activity.

The team will meet internally once each week to review completed work, discuss blockers and allocate the next set of tasks. Additional technical meetings may be arranged when integration or testing requires several members to work together. Progress meetings with the client are planned approximately fortnightly, subject to the client’s availability. The team will also attend scheduled facilitator meetings.

Each formal meeting will have an agenda and meeting minutes. The minutes will record the date, duration, attendees, main discussion points, decisions, action items, owners and due dates. Important decisions made through informal messages will be transferred to the meeting notes or the relevant GitHub issue so that they are not lost.

**Microsoft Teams group chat:** [CITS5206 Capstone Project Group Chat](https://teams.microsoft.com/l/chat/19:6ac1f08bbe3842ac9482806611f8d65c@thread.v2/conversations?context=%7B%22contextType%22%3A%22chat%22%7D)

**Microsoft Teams channel:** [Group 16 – CITS5206 Information Technology Capstone Project](https://teams.microsoft.com/l/channel/19%3ArHO415s3NliOh0Xvy5c56TTmpTiefwlMZl0XpurCo3E1%40thread.tacv2/Group%2016?groupId=4259f431-6994-4e09-90b6-cac70831356a&tenantId=05894af0-cb28-46d8-8716-74cdb46e2226&ngc=true)

**Meeting notes:** [Meeting Minutes](https://github.com/SanchiaLakkarvi/3D-printer-farm-interface/tree/main/Meeting%20Minutes)

---

## 3.4 Initial Product Backlog

The backlog has been developed from the initial client meeting and the agreed MVP. Items will be refined as the team receives the client’s sample G-code, approved PrusaSlicer configuration and access to Prusa Connect.

| Priority    | Backlog item                  | Expected outcome                                                                     |
| ----------- | ----------------------------- | ------------------------------------------------------------------------------------ |
| Must have   | Email-based authentication    | Users can securely log in and access features permitted for their role               |
| Must have   | User roles                    | Student/staff, farmer and administrator permissions are separated                    |
| Must have   | Printer list                  | Users can view printer status, material, colour and availability                     |
| Must have   | G-code upload                 | Users can upload a human-readable G-code file                                        |
| Must have   | G-code validation             | The system checks files against approved printer and slicing configurations          |
| Must have   | Time and cost estimation      | Print duration and estimated cost are displayed before submission                    |
| Must have   | Printer selection             | A compatible printer or the next available compatible printer can be selected        |
| Must have   | Job queue                     | Valid jobs enter a first-come, first-served queue                                    |
| Must have   | Job tracking                  | Users can view each job’s current status                                             |
| Must have   | Approval rules                | Jobs exceeding agreed time, material or configuration limits require approval        |
| Must have   | Farmer workflow               | Operators can record print completion, removal and readiness for collection          |
| Must have   | Basic notifications           | Relevant users are informed about major changes in job status                        |
| Must have   | Administration and reporting  | Administrators can view users, printers, jobs and basic usage information            |
| Must have   | Printer integration layer     | The system can communicate with Prusa Connect or a simulated printer interface       |
| Should have | Filament estimation           | The system estimates remaining filament using recorded spool data and completed jobs |
| Could have  | Expanded analytics            | More detailed printer, user and teaching-unit reporting is available                 |
| Future      | STL upload and online slicing | Users can upload STL files and slice them through the web platform                   |
| Future      | Camera monitoring             | Users or operators can view images or a live camera feed                             |
| Future      | Real payment processing       | Personal payments can be processed using an external payment gateway                 |

---

## 3.5 Initial User Stories

The following user stories describe the main outcomes expected from the MVP:

1. As a student or staff member, I want to log in using my email so that I can securely access the printing service.
2. As a user, I want to upload a pre-sliced G-code file so that I can submit a print without manually accessing Prusa Connect.
3. As a user, I want the system to validate my file so that incompatible or unsafe settings are identified before printing.
4. As a user, I want to view the estimated duration and cost so that I can make an informed decision before submitting the job.
5. As a user, I want to select a compatible printer or the next available compatible printer so that my job can be placed in the correct queue.
6. As a user, I want to track my job status so that I know whether it is awaiting approval, queued, printing, completed or ready for collection.
7. As a farmer, I want to update the status of completed prints so that users know when their work is ready for collection.
8. As an administrator, I want to approve jobs that exceed configured limits so that long or material-intensive prints remain controlled.
9. As an administrator, I want to view usage information so that printer utilisation and costs can be monitored and reported.
10. As a team member, I want to simulate printer states and responses so that development can continue when a physical printer is unavailable.

Acceptance criteria for individual user stories will be added to the relevant GitHub issues before development begins.

---

## 3.6 Milestones and Indicative Schedule

The project will be delivered through a series of milestones. Exact dates will be updated in the team’s Gantt chart according to the unit deadlines and client availability.

| Period          | Main activities                                                                                            | Expected milestone                              |
| --------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Weeks 1–3       | Client consultation, problem definition, MVP agreement, risk assessment and initial planning               | Project scope agreed and Assignment 1 completed |
| Weeks 4–5       | Architecture design, database schema, interface wireframes, API research and development-environment setup | Technical foundation approved by the team       |
| Weeks 6–7       | Authentication, role management, printer list, G-code upload and validation                                | First usable vertical prototype                 |
| Weeks 8–9       | Printer selection, queue management, cost estimation and approval workflow                                 | Core print-submission workflow completed        |
| Weeks 10–11     | Farmer workflow, notifications, administration functions, reporting and system integration                 | Feature-complete MVP                            |
| Week 12 onwards | End-to-end testing, printer testing, client feedback, defect correction and final documentation            | Validated final system and project handover     |

A separate Gantt chart provides detailed tasks, owners, dependencies, start dates, end dates and milestones.

**Gantt chart:** [3D Printer Farm Gantt Chart](https://uniwa-my.sharepoint.com/:x:/r/personal/24684008_student_uwa_edu_au/Documents/Microsoft%20Teams%20Chat%20Files/3D%20Printer%20Farm%20Gantt%20Draft%20.xlsx?d=w051a67770a5b42218d517edcfc95b31f&csf=1&web=1&e=O2KhUP)

---

## 3.7 Git and Pull Request Workflow

Development will take place in a shared GitHub repository. The `main` branch will contain stable and reviewed work. Members will create a separate branch for each feature, defect or documentation task. Branch names will follow an agreed format, such as `feature/gcode-upload`, `fix/queue-status` or `docs/setup-guide`.

When work is ready, the contributor will open a pull request describing what was changed, how it was tested and any related issue. At least one other team member will review the pull request before it is merged. Reviewers will check functionality, readability, security considerations, tests and compatibility with the existing system. Significant changes will not be merged directly into the `main` branch without review.

Merge conflicts will be resolved by the contributor in consultation with the member responsible for the affected component. Pull requests, reviews and commits will provide evidence of individual contributions.

---

## 3.8 Testing and Definition of Done

Testing will occur throughout development rather than only at the end. The client has approved the use of simulated printer states, mocked responses and shortened G-code files during development. This will allow the team to test normal workflows and failure conditions even when a physical printer is unavailable. A real end-to-end printer test is planned near the end of development.

A backlog item will be considered **Done** only when:

1. The agreed acceptance criteria have been met.
2. The implementation has been committed to the correct feature branch.
3. Relevant tests have been completed and passed.
4. Error cases and invalid inputs have been considered.
5. Another team member has reviewed the pull request.
6. The change has been merged without breaking existing functionality.
7. Related documentation has been updated.
8. The GitHub issue and project-board status have been updated.
9. The feature has been demonstrated to the team and, where appropriate, the client.

The team will use unit testing for individual functions, integration testing for interactions between the frontend, backend and database, and end-to-end testing for the main user workflows. Manual usability testing will also be used to determine whether the interface is understandable for students, staff, farmers and administrators.

---

## 3.9 Contribution Tracking

Individual contributions will be documented using GitHub commits, pull requests, code reviews, assigned issues, meeting attendance, meeting minutes, design files, testing records and written documentation. Each team member is expected to provide regular progress updates and raise blockers early.

The team will periodically review the project board to ensure that work is distributed fairly. Where a task is completed collaboratively, the issue or meeting notes will record the contribution of each member. This will provide transparent evidence for peer evaluation and allow the facilitator to understand how the group has worked together.

---

## 3.10 Managing Delays and Requirement Changes

Potential delays will be raised during weekly meetings or through the team’s Microsoft Teams channel as soon as they are identified. If a member cannot complete an assigned task, the team will assess its priority, dependencies and remaining effort. The task may be divided into smaller items, reassigned or rescheduled. Priority will remain on completing the agreed MVP before optional features are started.

Technical work will continue using mocks and simulated printer states if access to Prusa Connect, its API or a physical printer is delayed. If the client is temporarily unavailable, questions and assumptions will be documented and sent together to reduce repeated communication. Decisions that can safely be postponed will remain recorded as open issues.

New requirements will not be added directly to development without review. The requested change will first be recorded in the change log or a GitHub issue with its purpose, priority, estimated effort and effect on the schedule. The team will discuss whether the change is essential to the agreed MVP or should be treated as a future enhancement. Any material change to the MVP will be confirmed with the client and documented in the meeting notes.

If time becomes limited, optional features such as online STL slicing, live-camera integration, advanced scheduling, real payment processing and advanced analytics will remain outside the MVP. This protects delivery of the core workflow: login, G-code upload and validation, cost estimation, compatible-printer selection, queue submission, job tracking and operator completion.

---

# 4. Risk and Technology Assessment

This section evaluates the technology options for the 3D farm printer interface and identifies the risks associated with the proposed implementation. The evaluation is based on the Minimum Viable Product (MVP) agreed with the client and project team. The MVP includes:

1. User authentication
2. User authorisation
3. File validation
4. Printer selection and queue management
5. Printing workflow and notification

## 4.1 Technology Assessment

### 4.1.1 Frontend

#### Technology Options

| Option                   | Advantages                                                                                       | Disadvantages                     |
| ------------------------ | ------------------------------------------------------------------------------------------------ | --------------------------------- |
| **Next.js + TypeScript** | Strong React ecosystem, built-in routing, high developer productivity, easy deployment to Vercel | Higher learning curve             |
| **React + JavaScript**   | Flexible, large community                                                                        | No compile-time type checking     |
| **Vue.js**               | Simple and lightweight                                                                           | Smaller ecosystem within the team |

The team selected **Next.js + TypeScript** as the frontend stack. This option provides smooth integration with the Python FastAPI backend and reduces runtime errors through static typing.

### 4.1.2 Backend

#### Technology Options

| Option      | Advantages                                                | Disadvantages                  |
| ----------- | --------------------------------------------------------- | ------------------------------ |
| **FastAPI** | Async support, easy integration with validation libraries | Smaller ecosystem than Node.js |
| **Node.js** | Large ecosystem, lightweight                              | More manual configuration      |
| **Django**  | Strong admin features                                     | Overengineered for the MVP     |

The system requires REST APIs for communication, G-code validation, queue processing, notification services, and PrusaConnect API integration. **FastAPI** aligns well with these requirements and with the team’s existing Python experience.

### 4.1.3 Database and Queue

| Option         | Advantages                                                                             | Disadvantages                 |
| -------------- | -------------------------------------------------------------------------------------- | ----------------------------- |
| **PostgreSQL** | JSON support, open source, integrates well with FastAPI through SQLAlchemy or SQLModel | More administration           |
| **MongoDB**    | Flexible schema                                                                        | Weaker relational consistency |

The team chose **PostgreSQL** because it provides reliable relational database management and integrates well with the proposed backend stack. Both **SQLModel** and **SQLAlchemy** remain viable options; SQLModel is designed by the creator of FastAPI, while SQLAlchemy is the industry-standard Python ORM.

### 4.1.4 Authentication and Authorisation

UWA Single Sign-On was excluded from the MVP because the project is external to UWA. Authentication and authorisation will be implemented in FastAPI.

* Passwords will be hashed using a secure password-hashing library such as **bcrypt**.
* Authenticated users will receive access tokens.
* Authorisation will be enforced through **role-based access control (RBAC)** for administrators, students, and farmers.

### 4.1.5 Payment Processing

Real payment processing is excluded from the MVP. During development, **Stripe test/sandbox mode** will be used to simulate payments without introducing financial, legal, or compliance obligations. The system must not store real card details.

### 4.1.6 Printer Integration

The system will integrate with **PrusaConnect APIs** for printer selection, job submission, queue monitoring, and print-status updates. API limitations and availability are considered a significant project risk.

### 4.1.7 Testing

Testing will include:

* Unit testing for backend services and validation logic
* Integration testing for API endpoints and database operations
* Frontend component and workflow testing
* End-to-end testing for authentication, file upload, queue management, and printing workflows

---

## 4.2 Open Decisions

1. Staff billing model
2. Final pricing values
3. Buddy camera for real-time monitoring
4. Leftover filament statistics and notification
5. Exact threshold for long print jobs

---

## 4.3 Risk Assessment

| ID  | Risk                         | Likelihood (1–3) | Impact (1–3) | Score | Priority |
| --- | ---------------------------- | ---------------- | ------------ | ----- | -------- |
| R1  | PrusaConnect API limitations | 2                | 3            | 6     | High     |
| R2  | G-code validation failures   | 2                | 3            | 6     | High     |
| R3  | Queue concurrency bugs       | 2                | 3            | 6     | High     |
| R4  | Hosting configuration issues | 2                | 2            | 4     | Medium   |
| R5  | Weak authentication controls | 2                | 3            | 6     | High     |
| R6  | Unauthorised role access     | 2                | 3            | 6     | High     |
| R7  | Malicious file upload        | 2                | 3            | 6     | High     |
| R8  | Team member absence          | 2                | 2            | 4     | Medium   |
| R9  | Delayed client feedback      | 2                | 2            | 4     | Medium   |
| R10 | Underestimated workload      | 3                | 3            | 9     | High     |
| R11 | Git merge conflicts          | 2                | 2            | 4     | Medium   |
| R12 | Backup loss                  | 1                | 3            | 3     | Medium   |
| R13 | Data integrity alteration    | 1                | 3            | 3     | Medium   |

---

## 4.4 Risk Matrix

| Severity          | Rare     | Unlikely | Possible               | Likely | Almost Certain |
| ----------------- | -------- | -------- | ---------------------- | ------ | -------------- |
| **Catastrophic**  |          |          |                        |        |                |
| **Major**         | R12, R13 |          | R1, R2, R3, R5, R6, R7 | R10    |                |
| **Moderate**      |          |          | R4, R8, R9, R11        |        |                |
| **Minor**         |          |          |                        |        |                |
| **Insignificant** |          |          |                        |        |                |

**Probability scale:** Rare → Unlikely → Possible → Likely → Almost Certain
