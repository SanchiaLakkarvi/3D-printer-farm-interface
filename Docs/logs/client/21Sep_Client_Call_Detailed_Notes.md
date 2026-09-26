# Client Meeting Notes - 3D Printer Farm Interface

**Unit:** CITS5206 Capstone Project  
**Date:** 21 September 2026  
**Client:** Dr Christopher Lamb  
**Source:** Client meeting recording supplied by Group 16 (approximately 12 minutes)

## 1. Project Progress

- The team has prepared frontend dashboard views and is working on the queue and related backend integration. Access to the physical printer had only recently been provided, so a full live printer connection was not yet demonstrated.
- The frontend for email-code entry was described as ready, while backend and database work was still continuing.

## 2. Email Confirmation for the Demonstration

- The team explained that the current free email/SMTP arrangement limits its ability to send one-time codes for testing.
- The team asked whether a simpler email confirmation flow could be used temporarily in place of the intended code flow.
- Dr Lamb accepted a temporary approach **provided the reason is explained**. This did not remove the longer-term email-code requirement discussed previously.

## 3. Site Name

- The team suggested **Guild3D**. Dr Lamb did not favour using “Guild” in the name.
- He preferred a name connected to engineering generally, since the service is intended for more than one engineering area.
- The team should propose another professional, engineering-related name. **No final replacement name was agreed at this meeting.**

## 4. University Payment Integration

- The team may use a placeholder or prototype to demonstrate how payment would look and explain why the live University payment service is not yet connected.
- Dr Lamb described University account and approval prerequisites before the payment service can be configured. The exact internal account acronyms in the recording are unclear; the team should confirm them before documenting a technical integration plan.
- The necessary University setup is not expected to be available in time for the current project demonstration. A working live payment integration was not promised at this meeting.

## 5. Printer and Camera Network Access

- The relevant UWA IoT network identifies devices by MAC address and does not use the password-based connection expected by some equipment. This is complicating the client's attempt to connect the printer/camera setup.
- Dr Lamb is trying a Wi-Fi extender approach and hoped to make progress during the week. The camera was described as working separately but not yet on the University's network.
- The team should defer direct live integration questions until the network setup can be clarified. The long-term method for a remote application to reach the printer remains unresolved.

## 6. Mock Printer Server

- The team described using a mock printer server to continue development and demonstrate job flow while live printer data/access remains blocked.
- Dr Lamb agreed that the mock server is a suitable approach for the current project.
- He asked the team to document the connection problems so he can raise them with University IT. Resolving those institutional issues may take longer than the remaining project period.

## 7. Printer States and Safe Testing

- The team checked whether its planned printer statuses covered the important cases. Dr Lamb mentioned an additional **not ready** state, which can persist after a job completes until the printer is marked ready in the printer management system.
- Dr Lamb was comfortable with the team testing against the printer, including at the weekend, while it is idle and not running another print. The team should avoid interfering with an active job.

## 8. Further Support for Remote Connectivity

- Dr Lamb did not yet have an additional connection method to give the team. He said another existing setup can send prints remotely, but he did not know exactly how its connection was implemented.
- The team may ask the relevant printer service/support community about remote connectivity and describe the university project. Dr Lamb was willing to provide confirmation or guidance if support asks for it.
- Existing printer-management services do not fully meet the project's needs for controlled student access and the University's payment arrangements.

## 9. Actions and Open Questions

| Action | Owner / status |
| --- | --- |
| Explain the temporary email confirmation approach and its delivery limitation in the demo | Team |
| Propose an engineering-related name to replace Guild3D | Team; final name not agreed |
| Demonstrate a payment placeholder and record the University approval dependency | Team; confirm internal account terminology with Dr Lamb |
| Continue queue and job-flow development against the mock server | Team; approved by Dr Lamb |
| Record printer/network blockers for escalation to University IT | Team; Dr Lamb to follow up |
| Continue investigating the printer/camera network connection | Dr Lamb; outcome pending |
| Account for the printer's not-ready state and test only while idle | Team |
| Investigate remote connectivity through the relevant printer support channel | Team; Dr Lamb available for confirmation |

## Note on the Recording

The recording contains indistinct speech in parts of the payment and network discussion. These notes retain the confirmed decisions and leave unclear acronyms and implementation details open for confirmation rather than treating an automated transcript as exact wording.
