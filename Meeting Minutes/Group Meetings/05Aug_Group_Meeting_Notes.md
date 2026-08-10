# Group Meeting Notes – 3D Printer Farm Interface

**Date:** 5 August 2026
**Time:** 9:00 PM–9:55 PM
**Duration:** 55 minutes and 43 seconds
**Location/Platform:** Microsoft Teams
**Meeting Type:** Group Meeting
**Minutes Prepared By:** Sanchia

## Assignment 1 Responsibilities

* **Problem Statement – Nuwanga:** Explain what the team will build and why it is needed.
* **Client Communication and MVP Agreement – Sahil Pankajbhai Patel**
* **Project Planning and Management – Sanchia Recson Lakkarvi**
* **Risk and Technology Assessments – Su-Yeon Yang (Jesse)**
* **Summary, research on existing projects/resources, and other project resources – Han Nguyen**

## Initial Project Responsibilities

* **Sahil:** MVP planning and requirements
* **Nuwanga:** Backend development
* **Sanchia:** Frontend and UI development
* **Jesse:** Database design and implementation
* **Han:** Review the project requirements and choose an area of interest

## Tasks From the Facilitator Meeting

### 1. Facilitator Meeting Minutes – Jesse

Include:

* Meeting date, time, and duration
* Attendees
* Summary of what Sumayah explained
* Information about the required submissions
* Agreed meeting frequency and time
* Team member introductions and project responsibilities
* Discussions, decisions, action items, and important highlights

### 2. Meeting Agenda and Invitation – Sanchia

Prepare the agenda and send the meeting invitation to Sumayah.

## Documents to Prepare

### 3. Contingency Plan – Word Document

Include plans for:

* Team member absence
* Technical failure
* Unavailable printer or API
* Delayed client response
* Scope reduction

### 4. Methodology – Han

Use an Agile approach with short weekly iterations.

### 5. Gantt Chart – Nuwanga

Create the Gantt chart in Excel and include:

* Tasks
* Owners
* Dependencies
* Start and end dates
* Milestones

### 6. Weekly Task Management – Jesse

Use GitHub and a shared Excel file.

### 7. Project Guide or Log – Sahil

Store the following as Markdown files:

* Setup guide
* System architecture
* API details
* Database design
* User guide

Notion may also be used.

### 8. Learning Outcomes – To Be Discussed

Map the learning outcomes to activities and supporting evidence, such as:

* GitHub commits
* Designs
* Meetings
* Testing

## Items to Discuss

* Is a UI design required before frontend development?
* Should Figma be used to create the wireframes?
* Has a Prusa account been created?
* What actions and access are required for the API?
* UI design
* System architecture
* Team leader
* Final deliverables

## Required System Actions

* Log in
* View printers
* Upload and validate G-code
* Submit a job
* View the user’s jobs
* Change a job’s status
* View notifications
* View administrator metrics

## Essential User Features

* User login
* Three user roles
* Printer list
* Pre-sliced G-code upload
* G-code validation
* Printer selection
* Cost estimation and charge selection
* Job submission and queue
* Job tracking with the following statuses:

  * Submitted
  * Validation failed
  * Awaiting approval
  * Queued
  * Printing
  * Completed
  * Awaiting collection
  * Collected
  * Failed or cancelled
* Approval rule: Jobs exceeding the agreed threshold, such as more than 24 hours or 250 grams, require operator approval
* Simple usage analytics and farm dashboard
* Job history and audit information
* Basic notifications
* Printer integration layer

## Features Excluded From the MVP

* Uploading STL files and cloud-based slicing
* Multi-material or five-toolhead printing
* Full UWA SSO integration because access is unavailable; email login will be used instead
* Real financial payment processing through Stripe
* Advanced printer scheduling and optimisation
* Live camera or video streaming
* Automatic print recovery
* Complex editable slicing settings
* Predictive maintenance
* Filament tracking

## Proposed Technology

* **Notifications:** Firebase Cloud Messaging
* **Backend:** Python and FastAPI
* **Frontend:** Next.js and TypeScript
* **Database:** PostgreSQL
* **UI Design:** To be confirmed
* **System Architecture:** To be confirmed
* **Deployment:** Vercel
