# 5.1 Executive Summary

The project aims to develop a web-based 3D printer farm management system for UWA students and staff. The current printer-by-printer process using Prusa Connect requires users to be managed at the individual printer level and does not provide the centralised access, queue management, validation and usage visibility required for a larger shared printer farm.

The proposed system will provide a central management layer around the existing Prusa printer infrastructure. It will support role-based access, pre-sliced G-code upload and validation, compatible printer selection, queue management, job tracking, notifications and print collection. The system will support three roles: Student/Staff User, Printer Farmer/Operator and Administrator.

The agreed MVP focuses on the complete print-job workflow: login, G-code upload,  compatible printer selection, validation, queue submission, printing, status monitoring, notification and collection. Basic usage information will also be recorded. Final pricing values and the staff billing model have not yet been confirmed and are therefore not treated as fixed MVP requirements. Online slicing, advanced queue optimisation, camera integration, real payment processing and automatic remaining-filament tracking are outside the core MVP.

The project will use short Agile iterations supported by GitHub Projects, weekly team reviews and fortnightly client communication. The selected technology direction uses Next.js with TypeScript for the frontend, FastAPI for the backend and PostgreSQL for relational data management. A mock printer server and controlled physical-printer testing will support development where direct access to printers or printer interfaces is limited.

Key project risks include limitations of available Prusa interfaces, G-code validation failures, queue concurrency issues, authentication and authorisation weaknesses, malicious file uploads and underestimated workload. These risks will be managed through early integration investigation, approved G-code configurations, testing, role-based access control, file validation, mock printer simulation and prioritisation of the agreed MVP.

# 5.2 Research on Existing Projects and Resources

## 5.2.1 UWA UniPrint

UWA UniPrint provides a useful reference for a central university printing workflow, where users submit jobs through a shared service rather than interacting directly with individual printers (The University of Western Australia, n.d.). The proposed system applies this concept to 3D printing, where printer compatibility, material requirements and G-code configuration must also be considered.

## 5.2.2 Prusa Connect

Prusa Connect provides the existing web-connected environment for accessing and managing the UWA Prusa printers (Prusa Research, n.d.-a). However, UWA's current printer-by-printer process does not scale efficiently to a larger user group because users must be managed at the individual printer level and the current process does not provide the central printer-farm queue or university-level usage management required by the project.

Rather than replacing the existing printer infrastructure, the proposed system will provide a university-specific management layer around it. This layer will support role-based user access, central queue management, G-code validation, job and usage tracking, notifications, collection management and reporting. Final pricing values and billing arrangements remain subject to client confirmation.

## 5.2.3 Prusa Connect Printer SDK

The Prusa Connect Printer SDK is an important resource for investigating communication between printers and the Prusa ecosystem (Prusa Research, n.d.-b). It provides a basis for understanding printer events, communication and possible integration methods.

The SDK does not provide the complete university-level management functionality required by the project. The team will therefore investigate the SDK and available Prusa interfaces to determine how they can support the printer-integration layer, while implementing the required user, queue, validation and management functionality within the proposed system.

## 5.2.4 PrusaSlicer

PrusaSlicer converts 3D models into printer-ready G-code and provides printer and filament configuration profiles.

For the MVP, users will upload pre-sliced G-code generated using an approved PrusaSlicer configuration. The system will validate relevant printer, material and configuration information before allowing a job to proceed. Information such as estimated print duration and filament usage may be extracted from the G-code for job and usage information rather than treated as validation conditions.

This approach reduces the risk of incompatible files being submitted to physical printers while keeping the initial implementation manageable. Filament colour may be displayed to users but will not be used as a G-code validation condition because available colours may change.

## 5.2.5 Research Conclusion

The reviewed resources each support part of the proposed system but do not provide all of the university-specific management functionality required by the project.

| Resource | Contribution to the Project |
| --- | --- |
| UWA UniPrint | Reference for a central university printing workflow |
| Prusa Connect | Existing web-connected printer management environment |
| Prusa Connect Printer SDK | Resource for investigating printer integration |
| PrusaSlicer | Method for generating configured, printer-ready G-code |

The proposed system will therefore use the existing Prusa infrastructure and available resources while adding the role-based access, queue management, G-code validation, job and usage tracking, notifications, collection management and reporting functions required for the UWA 3D printer farm.

# 5.3 Other Project Resources

## 5.3.1 Hardware

The project will use the UWA-provided Orginal Prusa XL- 5T Input shaper 0.4 nozzel and Prusa CORE One HF0.4 nozzel printers. Access to physical printers will be controlled, so simulated printer behaviour will support development and testing when direct printer access is unavailable.

The Buddy3D camera image is used only as a visual reference in the prototype (Prusa Research, n.d.-c). Live-camera integration is outside the core MVP and may be considered as a future extension.

## 5.3.2 Software and Development Resources

Key software and development resources include:

- Next.js with TypeScript for frontend development;
- FastAPI for backend development;
- PostgreSQL for users, printers, jobs and usage data;
- Prusa Connect and available printer interfaces;
- Prusa Connect Printer SDK;
- PrusaSlicer and approved printer/material profiles;
- notification services;
- a mock printer server for development and testing; and
- GitHub for source control, issue tracking and project collaboration.

The client has not prescribed a specific technology stack. The team has selected technologies based on the MVP requirements, team capability, integration needs and development constraints. The technology assessment and associated risks are detailed in Section 4.

## 5.3.3 Client-Provided Resources

The client will provide:

- read-only Prusa Connect access;
- a sample G-code file;
- the approved PrusaSlicer configuration;
- guidance on required validation settings; and
- controlled access to physical printers for testing.

Read-only Prusa Connect access will support investigation and monitoring. The availability and capabilities of interfaces required for job submission and other printer-control operations will be investigated during development.

## 5.3.4 Testing Resources

A mock printer server will be developed to simulate the behaviour of the physical Prusa printers during development. It will provide simulated printer states and responses, allowing normal workflows and failure conditions to be tested when direct access to physical printers is unavailable.

Development testing will also use simplified G-code where appropriate. Controlled end-to-end testing with a physical printer will be performed near the end of development to validate the complete print-job workflow.

# References

Prusa Research. (n.d.-a). Prusa Connect and PrusaLink explained. Prusa Knowledge Base.
https://help.prusa3d.com/article/prusa-connect-and-prusalink-explained_302608?product=prusa-connect

Prusa Research. (n.d.-b). Prusa Connect SDK for Printer. GitHub.
https://github.com/prusa3d/Prusa-Connect-SDK-Printer

Prusa Research. (n.d.-c). Buddy3D camera printer view [Photograph]. Prusa Research.
https://www.prusa3d.com/cdn-cgi/image/width=750,format=auto,quality=85/content/wysiwyg/fotky/snapshot-Buddy3D%20Camera-1732719528.jpg

The University of Western Australia. (n.d.). UWA printing service.
https://print.uwa.edu.au

## AI-Use Acknowledgement

OpenAI ChatGPT was used during the preparation of this report to provide ideas and suggestions relevant to the project. 

The use of ChatGPT was undertaken in accordance with the University of Western Australia's guidance on the appropriate use of artificial intelligence in study and assessment.
