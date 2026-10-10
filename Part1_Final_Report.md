# Final Group Project Report 
## Project requirements and proposed solution

### Client need and agreed scope

The client required an easier platform to manage the university's Prusa 3D printers. Although Prusa Connect supports individual printer management, the client needs a unified system to coordinate users, print jobs, and queues across the university. The project is designed to facilitate seamless print submissions for students and staff while equipping operators with an integrated system to oversee workflows and manage collections.

### Key MVP Deliverables

- Authentication and role-based access control
- Upload of standard G-code print jobs
- Initial G-code validation and metadata extraction
- Validation of uploaded G-code against the target printer’s locked configuration
- Identification and display of compatible printers
- Printer selection and compatibility confirmation
- Print-job submission and queue management
- Basic print-job tracking and status information
- Notifications for job start, completion, and error/stopped states
- Farmer collection workflow for completed print jobs
- Basic usage reporting
### Solution and delivered features

#### System Architecture

The team developed a web application using a FastAPI backend and browser-based frontend, supported by Supabase for authentication and shared data services. A PrusaLink adapter enables printer communication, while Docker Compose manages local services and mock PrusaLink printers support testing without physical hardware.

#### Implemented Features

The implemented features include email-confirmed registration, role-based access control, G-code upload and validation, compatible-printer selection, per-printer queues with estimated print times, job tracking, notifications, and farm statistics. Additional functionality includes background printer synchronisation and an operator workflow for managing completed prints and collection.

#### Project Achievements and Limitations

Together, these features support the core workflow from job submission and printer monitoring to print collection. However, integration with physical printers remains unverified, while final G-code validation rules, pricing, cancellation and payment processes, certain operator and administrator interfaces, and hosted deployment remain incomplete or undecided. These areas are reserved for future development.


