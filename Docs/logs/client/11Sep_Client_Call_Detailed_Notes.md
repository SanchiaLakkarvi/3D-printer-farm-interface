# Client Meeting Notes - 3D Printer Farm Interface

**Unit:** CITS5206 Capstone Project  
**Date:** 11 September 2026  
**Client:** Dr Christopher Lamb  
**Source:** Group 16 client meeting notes, 11 September 2026

## 1. Authentication and Accounts

- Users should log in with an approved UWA email address. The accepted addresses may include student, staff and research accounts.
- A one-time verification code should be sent to the user's email.
- Users should be added to the application database only after their first login.
- Students receiving free printing credits can be uploaded separately; those credits should expire at the end of the semester.

## 2. Payment

- UWA Makers and UniPrint already use a University-approved payment platform. It appears to use predefined cart items rather than accepting an arbitrary amount from this application.
- Printing may therefore need cart items such as a first-hour item and additional-hour items or quantities.
- Dr Lamb will ask the relevant staff how the platform works and report back to the team.
- The current payment implementation may remain a temporary prototype until the University's process is confirmed.

## 3. Printer, Material and Colour Selection

- Students may choose a printer, material and available colour. Printer configurations can initially be simplified and treated consistently.
- Each printer may have two materials or colours configured. Administrators need to be able to edit printer types, materials, colours and configurations.
- Placeholder printer names and colours are acceptable for now.
- The initial supported materials are **PLA** and **PETG**, selected as safer options for the intended environment. **ABS** and **ASA** should not currently be offered because of potentially harmful fumes.
- Preferred colours are white and black, with blue, red and grey where available. Availability may depend on the printer or toolhead.
- The website may link to Prusa's material guide rather than reproducing material information.

## 4. Pricing and Failed Prints

- The proposed initial price is **$2.00 for the first hour** and **$0.50 for each additional hour**. The rates should help cover filament, maintenance and staffing, and must remain editable.
- If a printer or system fault causes a failed print, the job should be reprinted without charging the student again. The print farm absorbs the additional cost.

## 5. Print Queue

- Administrators and printer farmers should see the current print, upcoming jobs, estimated duration and completion time, and the assigned printer.
- Estimates should not assume that staff unload a printer immediately after every print.
- Estimated completion times should update regularly, ideally every minute.

## 6. History, Statistics and Priority Features

- Store print history in the database and provide clear statistics for the overall farm and for individual printers. The team may choose suitable charts or other visuals.
- The client's priority Prusa-related features are the admin/farmer print queue, current print status, estimated start and completion times, print history and printer usage statistics.
- Detailed telemetry and printer logs are not priorities. Remote movement controls and direct printer control through the website are not required. Printer movement must remain with authorised staff physically at the printer.
- Permanent storage of print files after completion is not required.

## 7. Camera

- A camera is optional rather than a core priority. If added, a simple IP camera or ESP32-based solution may be suitable.

## 8. Network and PrusaLink Access

- The Perkins printers are available only on the appropriate local network. The client provided access to an on-campus printer for testing, which should be reachable on the relevant UWA network.
- The team needs a long-term way for a production server outside that network to communicate with the printers. Investigate how the existing system handles remote communication.

## 9. Branding and Naming

- The client has **no mandatory logo or system name**. The team may choose an appropriate name and visual identity.
- The design should remain professional, readable and suitable for UWA. No particular new name was approved in these notes.

## 10. Action Items

| Action | Follow-up |
| --- | --- |
| Implement approved UWA email login and a one-time code | Team |
| Clarify the University payment platform with UWA Makers/UniPrint | Dr Lamb to contact the relevant staff; team to follow up |
| Apply the proposed $2.00 first-hour and $0.50 additional-hour pricing, with editable settings | Team |
| Allow administrators to update printer, material, colour and pricing settings | Team |
| Prioritise queue, time estimates, history and statistics | Team |
| Test PrusaLink using the on-campus printer and investigate production network access | Team |
| Start with PLA and PETG; exclude remote movement controls; treat camera support as optional | Team |

## 11. Useful Prusa References

The source notes list the Prusa Connect SDK Printer repository, *Prusa Connect and PrusaLink Explained*, the Prusa CORE One+ Gen 2 INDX 8-Tool information, and Prusa's filament material guide as technical references. Link the official material guide from the selection page if needed.
