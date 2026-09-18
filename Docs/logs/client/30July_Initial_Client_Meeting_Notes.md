# Client Meeting Notes – 3D Printer Farm Interface

**Unit:** CITS5206 Capstone Project
**Date:** 30 July 2026
**Duration:** 1 hour and 15 minutes
**Meeting Type:** Initial Client Requirements Gathering
**Location:** RM1.59
**Client:** Christopher Lamb
**Minutes Prepared By:** Sanchia

## Attendees

* Christopher Lamb – Client
* Sanchia Recson Lakkarvi
* Nuwanga
* Sahil Pankajbhai Patel
* Su-Yeon Yang (Jesse)

**Absent:** Han Nguyen – Out of the country

## 1. Meeting Purpose

The meeting was held to understand the client’s requirements, agree on the Minimum Viable Product (MVP), clarify the project scope, and discuss possible future enhancements.

## 2. Project Overview

The team will develop a web-based system that operates on top of Prusa Connect. It will allow students and staff to upload G-code files, select printers, submit print jobs, track their progress, and receive notifications.

The system aims to reduce manual administration and make the university’s 3D printer farm easier to manage.

## 3. Current Problems

The client explained the following limitations of the current system:

* Users must be manually invited to individual printers
* Managing many students is difficult
* There is no central printer-farm queue
* Billing, reporting, and usage tracking are limited
* Material and printer usage are not tracked centrally
* Printer error messages are sometimes unclear

## 4. Agreed MVP Requirements

The MVP should include:

* Email-based user login
* Three roles: Student/Staff, Farmer/Operator, and Administrator
* Human-readable G-code upload
* G-code validation using approved printer settings
* Printer selection
* First Come, First Served print queue
* Estimated printing time and cost
* Personal payment or approved unit-code selection
* Print-job status tracking
* Basic notifications
* Job approval rules
* Usage reports and statistics
* Printer integration through Prusa Connect

## 5. Proposed Workflow

1. The user logs in and uploads a G-code file.
2. The system validates the file.
3. The estimated printing time and cost are calculated.
4. The user selects a compatible printer.
5. The user chooses personal payment or an approved unit code.
6. The job enters the print queue.
7. The user receives notifications about the print status.
8. After printing, the farmer removes the item and marks it as ready for collection.
9. The user is notified, and the next print job can begin.
10. The uploaded file is deleted after collection, while its metadata is retained for reporting.

## 6. Important Rules and Decisions

* The system will operate on top of Prusa Connect rather than replace it.
* Only human-readable G-code will be supported in the MVP.
* Print settings will use approved PrusaSlicer configurations.
* Each printer will have one active material.
* Pricing will mainly be based on printing time.
* Jobs exceeding approximately 24 hours or 250 grams will require administrator approval.
* The next print must not begin until the farmer clears the printer.
* Payment details will not be stored.
* Uploaded files will be deleted after successful collection.

## 7. Testing

The client approved simulated testing during development. The team may simulate printer states, mock printer responses, test uploads, and use shortened G-code files.

A real end-to-end printing test should be completed near the end of development.

## 8. Future Enhancements

The following features are outside the MVP:

* STL upload and web-based slicing
* Live camera integration
* Multiple toolhead support
* Advanced queue prioritisation
* Online payment gateway
* Advanced filament tracking
* Advanced analytics and maintenance tracking

## 9. Resources to Be Provided by the Client

Christopher agreed to provide:

* Read-only Prusa Connect access
* Sample G-code files
* Approved PrusaSlicer configuration
* Printer access for testing
* Technical guidance

## 10. Action Items

### Client

* Provide Prusa Connect access
* Provide sample G-code and PrusaSlicer configuration
* Assist with printer testing

### Project Team

* Email the client requesting the agreed resources
* Finalise the MVP
* Design the system architecture and database
* Research the Prusa Connect API and SDK
* Create UI wireframes
* Plan G-code validation and queue management
* Arrange fortnightly progress meetings
