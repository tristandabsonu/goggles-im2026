# GOGgles IM2026

GOGgles is a human-in-the-loop grant-review prototype for the APS Innovation
Month 2026 **Build a Bureaucrat Bot** competition. It identifies avoidable
application issues, shows the relevant source and suggests what a person should
address. It does not score, approve, reject or write an application.

## Project context

Read these files in order:

1. [`docs/project-brief.md`](docs/project-brief.md) — problem, users and
   competition scope.
2. [`docs/design-document.md`](docs/design-document.md) — current behaviour,
   architecture, safeguards and limitations.

## Repository map

```text
backend/       FastAPI API and Gemini assessment workflows
frontend/      React source, dependencies and compiled production build
demo/naidoc/   Public source PDFs, synthetic fixtures and generation scripts
docs/          Two canonical context documents and the competition source PDF
tests/         No-cost tests and explicitly opt-in live Gemini checks
```

Local `.venv/`, `frontend/node_modules/` and `.env` are ignored development
state, not repository source.

## Run locally

Use Python 3.12:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Add an authorised Gemini key to `.env`, then run:

```bash
.venv/bin/uvicorn backend.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Verify

```bash
.venv/bin/python -m pytest
.venv/bin/python -m pip check
cd frontend
npm ci
npm run build
```

Frontend builds require Node 20.19 or newer. FastAPI serves `frontend/dist`, so
rebuild it after frontend changes.

Live tests and example-result regeneration spend API credit and require explicit
authorisation. Never send `demo/naidoc/test-cases/expected-results.md` to Gemini;
it is the local human answer key.

`render.yaml` prepares one FastAPI service that also serves the compiled
frontend. Deployment, account connection, paid-resource creation and publication
remain external actions requiring explicit authorisation.
