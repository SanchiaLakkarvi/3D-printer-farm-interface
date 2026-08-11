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
