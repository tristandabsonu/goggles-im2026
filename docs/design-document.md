# Technical design

## Core invariants

1. GOGgles provides comments and recommendations, never official decisions.
2. A person verifies sources, writes every change and retains responsibility.
3. Actionable findings are grounded in structured document references.
4. Writer fields are assessed independently; other draft answers are excluded.
5. Assessor mode may use the complete proposal for cross-section context.
6. A check never blocks submission or automatically rejects an application.
6. Documents are processed in memory and discarded after the request.
7. Only the NAIDOC dataset and named checks are claimed as validated.

## Architecture

The prototype is a React interface served by FastAPI. FastAPI validates uploads
and sends native PDF parts to the configured Gemini Flash model. There is no
database, OCR pipeline, separate worker service, persistent job queue or
authentication layer.

The runtime document order is stable—GOG, Application Form, supporting
documents, then submitted proposal when present—so Gemini's implicit prompt
caching can apply. Calls are deliberately sequential and progress is streamed
between real calls.

### Assessor workflow

The request bundle contains one GOG, one Application Form, optional supporting
documents and one submitted proposal.

```text
PDF bundle
  -> extract proposal fields from the Application Form and proposal
  -> select the supported field IDs
  -> assess each selected field with the complete labelled bundle
  -> return extraction, section results and threshold flags
```

Supported IDs are:

| ID | Implemented check |
|---|---|
| `funding_stream` | Conditional stream and requested-amount review |
| `budget` | Item scope, vagueness and cross-section clarification |
| `criterion_1` | Stream Three evidence review without scoring |
| `attachments` | Mandatory attachment manifest |

Other extracted fields are displayed transparently as unassessed fields. One
failed section becomes a section-level error without hiding successful results.

### Writer workflow

The Writer view already knows its form fields, so it does not run extraction.
Each marked answer is sent in a separate Gemini call with only the applicant-
facing GOG, Application Form and supporting documents. The Writer bundle has no
submitted-proposal slot.

The backend orders the fields, checks them sequentially and returns feedback by
field ID. An unexpected `clarified_elsewhere` budget classification is always
changed to `vague`, and all clarification evidence is removed before return.

### Result safeguards

- The GOG takes precedence over forms, guides and broad appendix examples.
- Findings, threshold flags and non-clear budget classifications require a
  structured source.
- Budget classifications are `in_scope`, `out_of_scope`, `vague` and, in
  Assessor mode only, `clarified_elsewhere`.
- Assessor clarification evidence must name an extracted section and provide an
  exact excerpt, evidence basis and reconciled amount. The excerpt must occur in
  that section and contain the amount; otherwise the item becomes `vague`.
- The private expected-results rubric is evaluated only after model calls and
  is not available through the demo-file API.

## HTTP and frontend behaviour

The working model endpoints are streamed form uploads:

- `POST /api/assessor/check/stream`
- `POST /api/writer/check/stream`

The demo-file route uses an explicit allow-list for public source PDFs and six
synthetic proposals. `/health` returns the service health status. FastAPI serves
the compiled React build and direct client routes.

The interface has four routes:

- `/` — Human Markup introduction plus the working Assessor and Writer views;
- `/how-it-works` — problem, process, limitations and production direction;
- `/example-results` — six captured Gemini checks rendered through the live
  result component without another model call.
- `/for-devs` — compact model, workflow and architecture rationale linked only
  from beneath the How-it-works workflow diagram.

Assessor and Writer inputs clear feedback that no longer matches the current
input. Mutable controls are locked while a check is running; non-mutating PDF
previews remain available. On narrow screens, budget results use stacked cards
instead of a horizontally scrolling table.

Captured examples are structured output from synthetic proposals, not invented
findings or the private answer key. The UI states that fresh model results can
vary and require human verification.

## Data and verification

`demo/naidoc/` contains the retained public program PDFs, synthetic application
sources and PDFs, the private expected-results rubric, a Writer smoke fixture
and the scripts that regenerate fixtures or captured examples. See its local
README before changing those files.

No-cost tests mock Gemini and cover upload validation, schemas, document
boundaries, streaming, field isolation, evidence guards and captured-result
validation. Paid live tests are explicitly marked and opt-in. Run the canonical
commands in the root `README.md`; do not record volatile pass counts here.

## Known limitations

- Only the named Assessor paths and marked Writer fields are implemented.
- General rule citations are model output and are not independently matched
  against PDF text. Cross-section clarification has only the narrow local gate
  described above.
- If extraction misses a supported proposal section, that check is skipped.
- PDF validation checks filename, non-empty content and the `%PDF-` header; it
  is not a full parser.
- Provider failures are reported in the request flow rather than through a
  production error service.
- Browser verification is a defined manual smoke pass, not an automated suite.

These are acceptable prototype constraints unless they break a named synthetic
scenario or overstate what was tested.

## Deployment shape

`render.yaml` prepares one paid Starter FastAPI service in Render's Singapore
region. GitHub Actions runs the no-cost backend checks and verifies a clean
frontend production build; Render's `checksPass` trigger deploys `main` only
after those checks pass. Render installs `requirements.txt`, serves the existing
`frontend/dist` build, uses `/health`, sets the tested `gemini-3.5-flash` model
and receives `GEMINI_API_KEY` as a dashboard secret. There is no database,
persistent worker service, disk or separate frontend service.

Deployment requires explicit authorisation. Minimum release verification is the
health route, frontend routes and assets, an allowed demo PDF, a 404 for the
private rubric, then one known Assessor scenario and one Writer scenario with
separate API-credit authorisation.
