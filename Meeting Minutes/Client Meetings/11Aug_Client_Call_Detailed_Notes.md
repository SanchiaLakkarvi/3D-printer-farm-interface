# Client Meeting Notes – 3D Printer Farm Interface

**Unit:** CITS5206 Capstone Project  
**Date:** 11 August 2026  
**Meeting Type:** Client Requirements Clarification / Prototype Review  
**Client:** Christopher Lamb  
**Minutes Prepared By:** Nuwanga

## 1. Meeting Purpose

The call focused on reviewing the current prototype, clarifying the required system behaviour, discussing user roles and billing, examining how G-code and PrusaSlicer settings should be handled, reviewing printer integration and error handling, and demonstrating how the physical printers operate.

The client was asked to comment mainly on functionality rather than the visual design of the prototype.

## 2. Prototype Review and Client Feedback

The team demonstrated the current prototype, including:

* Material selection
* Printer selection
* Job submission
* Queue position
* Job status changes
* User notifications
* Farmer notifications
* Admin usage information
* Material consumption information
* Top-user information
* Printer status information

The client said the overall functionality looked good and was happy with the way users could move between different parts of the system.

The client also responded positively to the different user access levels.

The UI shown during the call was treated as a reference rather than a final design. The discussion focused mainly on functionality.

## 3. Queue and Job Cancellation

The prototype demonstrated jobs entering a queue and receiving a queue position.

The following points were discussed:

* Jobs should enter a queue after submission.
* Queue position should be visible.
* The ability to cancel a queued job was discussed.
* The client responded positively to having a cancellation option.
* Detailed cancellation rules were not finalised during this call.

## 4. Billing and Different Rates

The client requested support for different printing rates for different accounts or groups.

The following billing ideas were discussed:

* Different rates may apply to students, staff, or different unit codes.
* A unit may receive a different hourly printing rate.
* A unit or student group could receive a printing allowance or credit.
* A lower rate could allow students in a particular unit to print more within the same allocated budget.
* The client described the main requirement as being able to vary the effective rate per hour for a unit or account.

A promo-code style approach was discussed as a simpler initial method because a complete payment system is not being implemented at this stage.

Possible promo-code behaviour discussed included:

* Applying a discount to a particular unit
* Applying a discount to staff
* Giving a different effective printing rate
* Allowing the code or discount to expire

The client was comfortable with implementing more detailed billing logic later, after the main printing workflow is working.

Exact prices, discounts, allowances, and billing-cycle rules were not finalised during this call.

## 5. Login and Account Management

The client was comfortable with a simple login approach using email or a similar identifier.

The following login and account behaviour was discussed:

* Users should have one account/profile.
* Users should not manually choose their role from the login page.
* Roles should be assigned in the backend.
* An administrator should be able to create or approve users and assign their role.
* A user may receive an email invitation to complete signup.
* The signup process could use details such as name, email, staff/student identifier, and role.
* Students should not be able to promote themselves to Farmer.
* A user who wants Farmer access should be approved by the person managing the space or by an Admin.
* Farmer and Admin users will most likely be associated with staff accounts.

The client described a model where an Admin enters the user details and role, after which the user receives an email and completes signup.

## 6. Role Hierarchy

Roles were discussed as hierarchical rather than completely separate accounts.

The expected behaviour discussed was:

* A Student/Staff user can submit print jobs.
* A Farmer can still submit their own print jobs.
* An Admin can still perform Farmer functions.
* An Admin can also submit their own print jobs.
* An Admin should not need to log out and sign in using a separate Student account to submit a print.
* A normal user can be upgraded to Farmer by an Admin.

The client preferred users to have one profile with permissions determined by their assigned role.

## 7. Target Printers

The project is currently targeting two printers.

The printers discussed were:

* Prusa XL with five tools
* Prusa CORE One / CORE One Plus

The client explained that the printers have different build volumes and capabilities.

The printer information displayed in the system should allow users to understand relevant information such as:

* Printer model
* Available material
* Available colour
* Printer status

## 8. Printer Build Volume and Compatibility

The client wants the system to check whether an uploaded print fits within the selected printer's physical build volume.

The client explained that a file sliced for a larger printer could potentially be submitted to a smaller printer even though the smaller machine cannot physically complete the print.

The web system should catch this problem before the physical printer attempts the job or produces an error.

The key requirement discussed was:

* Validate that the print dimensions are compatible with the selected printer.

## 9. Suggesting a More Suitable Printer

The client discussed a possible feature where the system recommends a more suitable printer when multiple printers can complete the same job.

The recommendation could consider:

* Print size
* Required material
* Printer availability
* Printer capability

An example discussed was a very small print selected for the larger Prusa XL while a smaller CORE One with the same material is available.

In that case, the system could tell the user that another printer may complete the job faster or is a more appropriate machine.

The client did not want the system to automatically move the job without the user's approval.

The expected behaviour discussed was:

1. Detect another suitable printer.
2. Inform the user that another printer may be a better option.
3. Allow the user to decide whether to change printers.

Machine-specific pricing was also discussed as a possible future way to encourage users to choose the most appropriate printer, but this was not finalised as an immediate requirement.

## 10. Local Slicing Instead of Cloud Slicing

The client recommended using locally sliced files rather than implementing cloud/web slicing for the current project.

Students can use PrusaSlicer on their own computer and upload the resulting G-code file.

The client explained that local slicing:

* Reduces server-side processing requirements
* Avoids many students trying to perform web-based slicing at the same time
* Simplifies the project
* Allows the project to focus on validating and submitting pre-sliced G-code

The client explicitly preferred dealing with pre-sliced files for the current project.

## 11. Standard PrusaSlicer Printer Profiles

The client demonstrated the standard/system presets available in PrusaSlicer.

The intended approach discussed was:

* Users select the correct supported printer in PrusaSlicer.
* Users use a standard/default printer profile.
* The project should not depend on the client's personal custom profiles.
* The uploaded G-code should be checked against approved printer settings.

A setup guide or configuration video was mentioned as a possible future way to explain which printer/profile users should select before slicing.

## 12. Print Profiles and Layer Heights

The client demonstrated that PrusaSlicer provides multiple print profiles.

The profiles can change settings such as:

* Layer height
* Print speed
* Acceleration
* Other related print settings

The client does not want students freely modifying these settings.

The preferred approach is for students to choose from a small set of approved standard profiles.

The system should check that the uploaded G-code matches an approved profile for the selected printer.

The client discussed possibly limiting the accepted profiles to a smaller set rather than supporting every available PrusaSlicer profile.

Example layer-height/profile values discussed included approximately:

* 0.10 mm
* 0.15 mm
* 0.25 mm
* A small set of around four approved profiles

The exact final list of approved profiles was not decided during the call.

If the uploaded file does not match an approved profile, the system should tell the user that the profile is not accepted and require the file to be re-sliced using an approved profile.

## 13. Protecting Standard Printer Settings

The client wants the validation process to detect important settings that have been changed away from the approved defaults.

The client explained that standard Prusa profiles are reliable for normal use and that students should not need to modify important settings.

Bed temperature was given as an example.

The client explained that a user could potentially change a value to an unsafe or incorrect setting, such as an excessively high bed temperature.

The validation should therefore help prevent incorrect settings from being sent to the physical printer.

## 14. Filament and Material Profiles

The client demonstrated the filament profiles available in PrusaSlicer.

The discussion included:

* Different filament types
* Different filament brands
* Generic filament profiles
* Prusa filament profiles

The client was not concerned about using a specific filament brand profile as long as an appropriate standard profile is used.

The important requirement is that the material type and the related default settings are suitable for the selected printer/material.

The system should check that the uploaded G-code matches an accepted material/filament configuration.

## 15. Filament Colour

The client does not want filament colour to be validated from the G-code.

The colour shown inside PrusaSlicer can be different from the physical colour loaded in the printer.

The client wants the online interface to show the actual material and colour currently loaded in the printer.

Users are responsible for checking the displayed physical colour before submitting the print.

This allows staff to change filament colours without needing to change the G-code validation rules.

For future multi-colour printing, users would need to understand which physical colour is loaded into each tool position.

## 16. Uploaded G-code Thumbnail / Preview

The client asked whether the system could show an image of the uploaded print after the G-code file is uploaded.

The client explained that thumbnail data is embedded inside Prusa-generated G-code.

The G-code can contain multiple thumbnail sizes.

The client suggested extracting one of these thumbnails and displaying it in the web interface.

The larger available thumbnail was discussed as the more useful option for display.

This could provide visual confirmation that the correct print file was uploaded.

The exact method for extracting or decoding the thumbnail was not finalised during the call.

## 17. Human-Readable G-code and Binary G-code

The client demonstrated that Prusa printers can support binary G-code.

Binary G-code is not human-readable in the same way as normal text G-code and may be harder to validate.

The client said the team does not need to support binary G-code if it creates unnecessary complexity.

The client was comfortable with the system supporting normal human-readable G-code only.

The proposed handling discussed was:

1. Detect or reject a binary G-code upload.
2. Inform the user that binary G-code is not supported.
3. Tell the user to disable the binary G-code option in PrusaSlicer.
4. Ask the user to export and upload a normal text G-code file instead.

## 18. G-code Metadata and Validation Area

The client opened and explained a normal text G-code file.

The file contains useful metadata and settings in addition to the movement commands used for printing.

The discussion identified information such as:

* Printer model
* Print-profile information
* Filament/material information
* Slicer settings
* Embedded thumbnail information

The client indicated that the validation work should mainly focus on the metadata/settings section of the G-code rather than checking every print movement instruction.

Large portions of the G-code are the actual movement/printing commands and do not need to be compared line by line for the intended validation.

## 19. Multi-Tool Prusa XL – Technical Context

The client demonstrated that the Prusa XL can use multiple tools/extruders.

The G-code contains information that can determine which tool/extruder is used.

The client's own printer setup includes personal configuration choices, but the project should rely on standard/default behaviour where possible.

The client explained that the physical printer configuration can be arranged to work with the standard profiles used by students.

This reduces the need for the web application to handle personal custom tool configurations.

## 20. Printer Dashboard and Printer Statistics

The client liked being able to see multiple printers together in the interface.

The client wants both material-usage and printer-time information.

The client explained that these are different measurements.

For example:

* A printer could use a large amount of material through a small number of very large jobs.
* The same printer could still be idle for long periods.
* Another printer may operate more frequently but use less material.

Therefore, the system should be able to show both material consumption and time/utilisation information.

Metrics discussed included:

* Total material consumption
* Printing hours
* Printer utilisation
* Percentage of time printing
* Percentage of time idle
* Usage over a selected period
* Usage per printer
* Material consumption per printer

The client referred to statistics similar to those available in existing printer-management software.

A period such as the last 90 days was used as an example.

The client also liked the top-user information shown in the prototype.

## 21. Admin Printer and Material Management

The client was comfortable with an Admin being able to manage printer-related configuration.

This could include:

* Adding a printer
* Updating printer information
* Updating the material loaded in a printer
* Updating filament information

The client explained that this is useful because printers and materials can change over time.

## 22. Farmer Dashboard

The Farmer view should provide useful operational information about the printers.

The discussion included visibility of:

* Printer status
* Current print/job
* Material information
* Printer errors
* Printer-related alerts

The client liked the prototype's printer-card style view and the ability to see the status of multiple printers.

## 23. Printer Error Demonstration

During the physical printer demonstration, a filament-related problem occurred.

The client used this as an example of the type of physical problem a Farmer may need to handle.

The client explained that PrusaConnect may initially show a more specific error message.

After a period of time, the detailed error can disappear and be replaced by a more general message such as a request to check the printer.

The client said this is not very useful for remote monitoring.

If possible, the system should capture the detailed error information when it first appears and retain it for the Farmer.

The Farmer should continue to be able to see that the printer requires attention even if the original detailed message later disappears from PrusaConnect.

## 24. Crash Detection and Camera Use

The client also demonstrated a crash-detection condition.

The message indicated that a crash had occurred but did not fully explain the physical situation.

The client said that if a camera is available, attaching an image to the error notification would be useful.

A photo could help the Farmer understand what physically happened when the text error message is unclear.

Camera-assisted error diagnosis was discussed positively but was not finalised as a mandatory immediate core requirement.

## 25. Error Recovery – Technical Context

The client demonstrated that the printer can recover from some errors after the physical problem is corrected.

The client explained that some issues are more likely near the beginning of a print.

Once the problem is resolved, the machine may be able to continue printing.

The client also explained that people with printer experience may be required to resolve some physical machine problems.

This supports the need for the Farmer/Operator role.

## 26. PrusaConnect / API Integration

The team asked how printer status and error information could be obtained from PrusaConnect.

The client expects that some form of API or integration should allow access to printer information, but the exact method still needs investigation.

The required integration direction discussed includes:

* Upload/send a G-code file to a printer
* Tell the printer to start/submit the print
* Receive printer status information
* Receive print-completion information where possible
* Receive error information where possible

The client would like detailed error messages to be captured if the API exposes them.

If exact completion information cannot be retrieved, the client said an approximate completion notification based on estimated G-code print duration would still be acceptable.

Direct printer status is preferred if it is available.

## 27. Possible Printer Integration Approaches

Two possible approaches were discussed:

* Direct API/interface access to the printer/Prusa system
* Creating a user/account with printer access and using that account for communication with the printers

The team will need to investigate which approach is practical.

The exact integration method was not finalised during this call.

## 28. Development Access to the Printers

The client is willing to provide the team with access to the printers.

The discussion included:

* Read access for investigating printer information
* Write access when the team is ready to test submitting jobs

The team said it may request write access after more of the system is ready.

The client said the team should let him know when access is required.

## 29. Safe Testing with Shortened G-code

The client described a safe method for testing printer integration without repeatedly producing real prints.

A G-code file can be shortened by removing the actual printing/body section while keeping the required starting and ending sections.

The shortened file can be used to:

* Initialise the printer
* Perform the required start sequence
* Test file submission
* Test printer communication
* Test status changes
* Test notifications
* End/shut down normally

This allows repeated integration testing without producing a physical object each time.

The client was comfortable with the team using this approach.

## 30. Printer Start Sequence – Technical Demonstration

The client demonstrated part of the physical printer start sequence.

The printer performs operations such as:

* Heating
* Homing
* Selecting/using a tool
* Probing the print area
* Preparing the build plate before printing

The client also explained that the Prusa XL uses a modular heated bed and only relevant heater zones may be active for a particular print area.

These details were explained as technical printer behaviour rather than separate web-system requirements.

## 31. Print Progress and Estimated Time

The client explained that print progress and estimated time are not always directly equivalent.

Printer speed can change throughout the print.

The client demonstrated that minimum layer-time settings can slow the printer when a layer is very small so the material has enough time to cool.

As a result:

* Percentage of G-code completed may not equal percentage of print time completed.
* A print may be far through the file but still have a significant amount of time remaining.
* Some sections of a print may run faster than others.

This should be considered if the web interface displays progress percentage or estimated remaining time.

## 32. Minimum Layer Time – Technical Explanation

The client explained that the slicer/printer can slow down when layers are completed too quickly.

This allows the printed material to cool before the next layer is placed on top.

The printer may also increase cooling fan activity.

This behaviour is one reason print-time estimates and file-based progress can differ.

## 33. Physical Print Completion and Collection

The client demonstrated the removable spring-steel build plate.

The plate is magnetically attached to the printer.

After printing:

* The plate should be allowed to cool.
* The plate can be removed.
* The plate can be flexed to release the printed object.

The client explained that removing the object while it is still too hot can cause the object to bend or deform.

This provides physical context for the Farmer collection step after the print is completed.

## 34. Layer Height and Print Quality – Technical Explanation

The client explained that 3D printed objects are created by stacking layers.

The client demonstrated that:

* Smaller layer heights create smoother-looking surfaces.
* Larger layer heights make layer lines more visible.
* Curved surfaces show the difference more clearly.
* Smaller layers usually improve appearance but can increase printing time.
* Larger layers can reduce printing time but may reduce surface detail.

This was part of the explanation for why standard approved profiles should be used instead of allowing users to freely change all slicer settings.

## 35. Important Requirements and Decisions from This Call

The main directions discussed during the call were:

* Use pre-sliced G-code rather than building cloud slicing for the current project.
* Prefer normal human-readable G-code rather than requiring support for binary G-code.
* Validate the selected printer model and physical build-volume compatibility.
* Validate uploaded G-code against approved printer and print profiles.
* Validate the material/filament configuration.
* Do not validate filament colour from the G-code.
* Display the actual loaded material and colour in the web interface.
* Keep user roles controlled by the backend.
* Use a hierarchical role model so Farmer and Admin users retain print-submission capability.
* Support queueing and job cancellation behaviour.
* Support both material-consumption and printer-utilisation statistics.
* Consider suggesting a more suitable compatible printer without automatically changing the user's selection.
* Investigate retrieving printer status and error messages through Prusa integration.
* Preserve detailed printer errors where possible before they become generic messages.
* Use shortened G-code for safe repeated integration testing.

## 36. Items Not Finalised During the Call

The following items remained open or were discussed as later-stage work:

* Exact pricing for students, staff, and different unit codes
* Exact promo-code/discount implementation
* Exact billing-cycle behaviour
* Exact final list of approved print profiles/layer heights
* Exact method for extracting G-code thumbnails
* Exact PrusaConnect/API integration method
* Exact availability and persistence of detailed printer error messages through the API
* Machine-specific pricing
* Camera images attached to error notifications
* More advanced billing behaviour after the core system is working

## 37. Follow-Up / Investigation Items

Based on the questions and unresolved points raised during the call, the team needs to continue investigating:

* How to read the required printer/profile/material information from human-readable G-code
* How to check build-volume compatibility from the uploaded file
* How to identify approved PrusaSlicer profiles from G-code metadata
* How to detect binary G-code and provide a useful rejection message
* How to extract embedded G-code thumbnails
* How to access printer status through PrusaConnect or another available interface
* How to capture printer error messages before detailed information disappears
* How to submit jobs safely through the printer integration
* How to calculate or display useful printer-utilisation metrics
* How to implement unit/account-specific billing rules at a later stage
