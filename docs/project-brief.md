# Project brief

GOGgles is a prototype entry for the **Build a Bureaucrat Bot — APS Innovation
Month 2026** competition. Entries close at 9am Monday 20 July 2026. The
[original competition brief](reference/competition-project-description.pdf) is
retained as source material but is not required reading for normal development.

## Problem and idea

Grant applicants can miss avoidable requirements hidden in dense Grant
Opportunity Guidelines (GOGs). Assessors then spend time on mechanical checks
instead of merit and context.

GOGgles demonstrates one grounded interaction: identify a possible issue, show
the relevant source, suggest what a person can address, and leave all writing
and decisions to that person.

It has two views:

- **Applicant** checks selected draft fields independently and gives inline
  guidance. It never writes replacement text or uses one draft answer to excuse
  ambiguity in another. Its advice never blocks submission or automatically
  rejects an application; an applicant may continue when a field is unchecked,
  flagged or the check fails.
- **Assessor** checks a submitted proposal against supplied program documents
  and returns cited review comments. It never scores, approves or rejects.

## Competition scope

The demonstrated dataset is the public **2026 NAIDOC Local Grants Opportunity**
plus six fictional applications: five planted-issue scenarios and one clean
control. The implemented Assessor checks are funding stream, budget, Stream
Three criterion and attachment manifest. Applicant checks cover activity
description/alignment, the conditional Stream Three criterion, budget and a
metadata-only attachment checklist.

The document inputs are replaceable to demonstrate an adaptable pattern, but
only the NAIDOC set and those named paths have been validated. GOGgles is not a
general grant-assessment service.

Out of scope for the competition prototype are real applicant data, entity or
attachment verification, persistent storage, system integration, authentication,
broad multi-program validation and production security/privacy governance.

## Guardrails

- Use only public, synthetic, fictional or otherwise authorised information.
- Treat every output as review assistance that a human must verify.
- Preserve source references and make model variability visible.
- Keep Applicant draft fields isolated from one another.
- Do not expose or send the private expected-results rubric to Gemini.
- Uploaded documents exist in memory for one request and are not stored.

Production work would require multi-program validation, co-design with users,
cultural consultation, privacy and security assessment, integration design and
accountable service ownership.

## Success and release status

Success means a judge can access the prototype, understand the problem quickly,
see a convincing synthetic interaction, verify its source grounding and see
that a human remains responsible.

The application, synthetic dataset, captured example results, automated checks
and one-service Render configuration are implemented. Nothing has been deployed,
published or submitted. Remaining release work is:

1. Run the final Assessor and Applicant live browser smoke checks only with API
   credit authorisation.
2. Rebuild and verify the release artifact.
3. Deploy and verify a judge URL only with deployment authorisation.
4. Confirm Digital Profession membership and prepare the bot card and entry
   email.
5. Send the entry only with explicit authorisation.
