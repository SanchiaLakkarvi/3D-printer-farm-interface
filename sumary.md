# 5.1 Project Summary

The project aims to develop a web-based 3D printer farm management system for UWA students and staff. It will provide a central interface for submitting and managing print jobs across the available Prusa XL and CORE One printers.

The project addresses the gap between printer-level management and university-level resource management. While Prusa Connect provides remote printer monitoring and control, the proposed system extends these capabilities with university-specific user management, centralised queuing, G-code validation, cost and usage tracking, material tracking, notifications and print collection. This supports the project's objective of reducing printer-level administration and providing a more scalable printing service.

The system will act as a management layer over Prusa Connect or the relevant printer APIs. Users will be able to authenticate according to their role, upload and validate pre-sliced G-code, select a compatible printer based on availability and material, submit jobs to a central first-come, first-served queue, monitor printing progress, receive printing and collection notifications, and track basic printing costs and usage. Filament colour may be displayed to users but will not be used as a G-code validation condition.

The system will support three roles: Student/Staff User, Printer Farmer/Operator and Administrator. Administrators will have access to users, printers, jobs, usage and reporting information, while farmers will manage printer status, completed or failed jobs, print collection, printer errors and maintenance actions.

The MVP will focus on the complete printing workflow from G-code upload and validation through printer selection, queue submission, printing, monitoring, notification and collection. Online slicing, advanced queue optimisation, camera integration, real online payment processing and automatic remaining-filament tracking will be treated as optional or future extensions. Payment simulation may be used during development rather than real payment processing.

# 5.2 Research on Existing Projects and Resources

## 5.2.1 UWA UniPrint

UWA UniPrint provides a useful reference for a university-oriented printing workflow, particularly the concept of submitting jobs through a central service rather than interacting directly with individual printers. The proposed system adopts this centralised approach but extends it for 3D printing, where printer compatibility, material and G-code configuration must also be considered.

## 5.2.2 Prusa Connect

Prusa Connect provides the existing web-connected environment for accessing and managing the Prusa printers. However, the current Prusa Connect-based process does not scale effectively to a larger university user base because users must be managed at the individual printer level, and the current process does not provide the centralised printer-farm queue and university-level usage management required by the project.

Rather than replacing Prusa Connect, the proposed system will build a university-specific management layer around the existing printer infrastructure. This layer will provide functions required by the client, including user roles, farm-wide queuing, unit-code usage and cost tracking, G-code validation, collection management and university-level reporting.

## 5.2.3 Prusa Connect Printer SDK

The provided Prusa Connect Printer SDK is an important resource for investigating communication between printers and Prusa Connect. It provides a basis for understanding printer events, communication and integration with the Prusa ecosystem.

However, the SDK is not a complete university printer-farm application. The project will therefore investigate how its capabilities and the available Prusa interfaces can support the printer-integration layer while implementing university-specific functionality separately.

Multi-printer queue management remains a key requirement for this project. The proposed system will therefore provide a dedicated farm-wide queue, initially using a first-come, first-served approach.

## 5.2.4 PrusaSlicer

PrusaSlicer converts 3D models into printer-ready G-code and provides printer and filament configuration profiles.

For the MVP, students will primarily upload pre-sliced G-code generated using an approved PrusaSlicer configuration. The system will validate relevant information including printer compatibility, material type, printer profile, temperature settings, estimated printing duration and filament usage before allowing the job to proceed.

This approach reduces the risk of incompatible files being sent to physical printers while keeping the initial implementation manageable. Filament colour will not be used as a validation condition because available colours may change.

## 5.2.5 Research Conclusion

The research indicates that no single existing resource completely satisfies the project's requirements:

| Resource | Contribution to the project |
| --- | --- |
| UWA UniPrint | Reference for a central university printing workflow |
| Prusa Connect | Existing web-connected printer management infrastructure |
| Prusa Connect SDK | Resource for investigating printer integration |
| PrusaSlicer | Approved method for generating printer-compatible G-code |
| Proposed system | Adds university-specific user management, centralised queueing, validation, cost and usage tracking, notifications, collection management and reporting |

Therefore, the proposed system will use existing resources and Prusa technologies while adding the university-specific management functions required for the UWA printer farm.

# 5.3 Other Project Resources

## 5.3.1 Hardware

The project will use the UWA-provided Prusa XL and Prusa CORE One printers. Camera integration has been identified as an optional future feature rather than part of the core MVP.

## 5.3.2 Software and Development Resources

Key software resources include:

- Prusa Connect and relevant printer APIs;
- Prusa Connect Printer SDK;
- PrusaSlicer and approved printer/material profiles;
- a web front-end and back-end framework;
- a database for users, printers, jobs and usage records;
- notification services; and
- GitHub for source control and project collaboration.

The client has not prescribed a technology stack, allowing the team to select technologies appropriate to the project's requirements. The team's selected technologies and their assessment are detailed in Section 4, including Next.js with TypeScript for the frontend, FastAPI for the backend and PostgreSQL for the database.

## 5.3.3 Client-Provided Resources

The client will provide:

- read-only Prusa Connect access;
- a sample G-code file;
- the approved PrusaSlicer configuration;
- guidance on required validation settings;
- access to a camera-equipped printer; and
- controlled access to physical printers for testing.

## 5.3.4 Testing Resources

A mock printer server will be developed to simulate the behaviour of the physical Prusa printers during development. The server will provide simulated printer states and responses, allowing normal workflows and failure conditions to be tested when physical printers are unavailable. Development testing will also use simplified G-code where appropriate, with a real end-to-end printer test planned near the end of development.