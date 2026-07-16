# Backend workflows

GOGgles composes its two workflows from the same labelled-document and
structured-result pattern:

- `extract_assessable_sections(...)` followed by `iter_assessment_steps(...)`
  for Assessor mode;
- `iter_writer_assessment_steps(...)` for Writer mode.

Documents are sent to Gemini as native PDF inputs. Uploaded bytes and extracted
sections live only for the request and are not stored in a database.

## Document bundles

The Assessor bundle contains:

- one GOG;
- one Application Form;
- zero or more supporting documents; and
- one submitted proposal.

The Writer bundle contains the applicant-facing GOG, Application Form and
supporting documents. Its type has no submitted-proposal field.

The GOG is the primary rule source. Forms and guides can add instructions or
context but cannot override it.

## Assessor workflow

```text
PDF bundle
  -> pass 1: extract proposal fields
  -> select the four supported field IDs
  -> pass 2: assess each supported field sequentially
  -> combine extraction, findings and flags
```

Pass 1 receives only the Application Form and submitted proposal. It extracts a
small set of grouped answers as structured JSON, including heading, type, exact
text, application order and source pages. Other substantive fields may be
returned as `generic` for transparent display.

Pass 2 supports four IDs:

| ID | Check |
|---|---|
| `funding_stream` | Conditional stream and amount review |
| `budget` | Item-level scope, vagueness and cross-section clarification |
| `criterion_1` | Stream Three criterion evidence, without scoring |
| `attachments` | Mandatory attachment manifest |

Each pass-two call receives the complete labelled bundle. This lets Assessor
mode recognise information elsewhere in the proposal. One failed section is
returned as a section error without discarding successful results.

The frontend uses `POST /api/assessor/check/stream`. The stream reports
extraction, the supported headings found, each real review as it begins and the
final `AssessorCheckResult`.

## Writer workflow

The frontend already knows its form fields, so Writer mode does not run
extraction.

1. The frontend submits only fields marked for AI review.
2. The backend validates and orders those fields.
3. Each field is sent in a separate Gemini request with the Writer document
   bundle.
4. Results are returned under the field IDs for inline display.

No Writer call receives another draft answer. A vague budget label therefore
cannot be silently resolved using an activity description.

The frontend uses `POST /api/writer/check/stream`. It reports one real stage per
field followed by the normal `WriterCheckResult`.

## Result rules

- Findings are comments or recommendations, never official decisions.
- Actionable findings, threshold flags and non-clear budget classifications
  require at least one structured source.
- Budget items use `in_scope`, `out_of_scope`, `vague` or
  `clarified_elsewhere`.
- Generic extracted sections are displayed but not assessed.
- Results are restored to application order.

For `clarified_elsewhere`, the model must identify a pass-one section and return
an exact excerpt, evidence basis and reconciled amount. The backend keeps the
classification only when the excerpt occurs in that section and contains the
requested amount. Otherwise it changes the item to `vague`. Accepted headings
and pages are copied from pass one.

Writer budget checks have a stricter postcondition because each draft field is
assessed in isolation: an unexpected `clarified_elsewhere` classification is
always changed to `vague`, and clarification evidence is removed before the
result is returned.

This is a narrow guard for the demonstrated cross-section behaviour, not a
general citation-verification system.

## Errors, latency and caching

Model calls are synchronous and sequential by design. A full Assessor request
takes roughly 60–180 seconds, and the UI reports progress between calls. This is
simple to explain and adequate for the competition; there is no queue, polling
service or worker system.

Shared documents are kept in a stable order so Gemini's implicit prompt caching
can apply. Usage logging records input, output, thinking, cached and total
tokens.

## Tests

Fast tests mock Gemini and cover validation, schemas, request construction,
field isolation, streaming and evidence handling. Paid live tests cover the six
synthetic applications and Writer smoke checks.

Never send `demo/naidoc/test-cases/expected-results.md` to Gemini. It is the
human answer key used after a response returns.
