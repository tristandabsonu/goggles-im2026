import asyncio
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app import _DEMO_FILES, create_app
from backend.config import Settings
from backend.models import (
    AssessorCheckResult,
    ExtractedSection,
    SectionExtractionResult,
    WriterCheckResult,
)


def make_settings() -> Settings:
    return Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )


async def post_to_app(app, *, files, path="/api/assessor/check/stream"):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post(path, files=files)


async def get_from_app(app, path: str):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get(path)


def parse_event_stream(body: str) -> list[dict]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def test_health_route() -> None:
    app = create_app(make_settings())

    async def make_request():
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                return await client.get("/health")

    response = asyncio.run(make_request())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_demo_file_route_serves_only_named_pdf_assets() -> None:
    assert set(_DEMO_FILES) == {
        "gog",
        "application_form",
        "applicants_guide",
        "application_01",
        "application_02",
        "application_03",
        "application_04",
        "application_05",
        "application_06",
    }
    assert all(path.is_file() for path in _DEMO_FILES.values())
    assert all(path.read_bytes().startswith(b"%PDF-") for path in _DEMO_FILES.values())
    assert _DEMO_FILES["gog"].name == (
        "NAIDOC 2026 Local Grants Opportunity - Grant Opportunity Guidelines.pdf"
    )
    assert _DEMO_FILES["application_form"].name == (
        "NAIDOC 2026 - Sample Application Form.pdf"
    )
    assert _DEMO_FILES["applicants_guide"].name == (
        "NAIDOC 2026 Local Grants - Applicants Guide.pdf"
    )


def test_demo_pdf_is_served_inline_for_in_app_preview() -> None:
    app = create_app(make_settings())
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/demo/files/{key}"
    )

    response = asyncio.run(route.endpoint("gog"))

    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline;")


def test_compiled_frontend_is_served_from_the_root() -> None:
    frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    index = (frontend_dist / "index.html").read_text()

    assert "GOGgles IM2026" in index
    assert "/assets/" in index
    assert any((frontend_dist / "assets").glob("*.js"))
    assert any((frontend_dist / "assets").glob("*.css"))
    javascript = "\n".join(
        path.read_text() for path in (frontend_dist / "assets").glob("*.js")
    )
    assert "—" not in index
    assert "—" not in javascript
    assert "Extracting assessable sections" in javascript
    assert "See how it works" in javascript
    assert "Try it now" in javascript
    assert "Skip to main content" in javascript
    assert "Put judgement back at the centre of grant assessment." in javascript
    assert "Use GOGgles in three steps." in javascript
    assert "Model choice, request flow and architecture trade-offs." in javascript
    assert "The technical choices behind GOGgles." in javascript
    assert "Request shape" in javascript
    assert "Stateless by design" in javascript
    assert "separate worker service or persistent job queue" in javascript
    assert "Small on purpose" in javascript
    assert "intentionally limited to the named NAIDOC checks" in javascript
    assert "Claude models were also trialled during development." in javascript
    assert "Developer:" in javascript
    assert "Tristan Garcia" in javascript
    assert "https://au.linkedin.com/in/tristandabsonu" in javascript
    assert (
        "Competition prototype · Public and synthetic demo data only" not in javascript
    )
    assert "upload your own test proposal" in javascript
    assert "upload an authorised one" not in javascript
    assert "clear it to upload another test PDF" in javascript
    assert "clear it to upload another authorised PDF" not in javascript
    assert "00 000 000 000" in javascript
    assert "First Nations storytelling" in javascript
    assert "facilitator (6 hours at $100/hour)" not in javascript
    assert "Workshop costs" in javascript
    assert "NAIDOC T-shirts for participants" in javascript
    assert "What happens after you click" in javascript
    assert "AI can be confidently wrong." in javascript
    assert "A competition prototype, not a finished service." in javascript
    assert "See completed examples while you wait." in javascript
    assert "Compare this run with the examples." in javascript
    assert "sourced publicly from grants.gov.au" in javascript
    assert "contain no real applicant information" in javascript
    assert "This section raised the human-review flag shown above." in javascript
    assert "Extracted proposal sections" in javascript
    assert "Not assessed" in javascript
    assert "sent to Gemini for this check" in javascript
    assert "GOGgles never blocks submission or auto-rejects" in javascript
    assert "GOGgles cannot stop or auto-reject an application" in javascript
    assert "GOGgles is not a submission gatekeeper" in javascript
    assert "See GOGgles results without the wait." in javascript
    assert "Live checks usually take 60–180 seconds." in javascript
    assert "About model variability" in javascript
    assert "live runs may use a different configured model" in javascript
    assert "homepage may use a different configured model" not in javascript
    assert "Gemini 3.5 Flash" in javascript
    assert "Captured Gemini output" not in javascript
    assert "Captured examples" not in javascript
    assert "Selected synthetic proposal" not in javascript
    assert "View synthetic proposal" not in javascript
    assert "GOGgles synthetic application expected-results rubric" not in javascript
    assert "Claude is reading the supplied PDFs" not in javascript
    for filename in (
        "NAIDOC 2026 Local Grants Opportunity - Grant Opportunity Guidelines.pdf",
        "NAIDOC 2026 - Sample Application Form.pdf",
        "NAIDOC 2026 Local Grants - Applicants Guide.pdf",
    ):
        assert filename in javascript


def test_standalone_pages_support_direct_navigation() -> None:
    app = create_app(make_settings())

    for path in (
        "/how-it-works",
        "/how-it-works/",
        "/example-results",
        "/example-results/",
        "/for-devs",
        "/for-devs/",
    ):
        response = asyncio.run(get_from_app(app, path))
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "GOGgles IM2026" in response.text

    missing = asyncio.run(get_from_app(app, "/does-not-exist"))
    assert missing.status_code == 404


def test_assessor_stream_reports_real_stages_then_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_section = ExtractedSection(
        id="budget",
        header="Project budget",
        type="budget",
        text="Event delivery: $5,500",
        order=1,
        source_pages=[18],
    )
    ignored_section = ExtractedSection(
        id="organisation_details",
        header="Organisation details",
        type="generic",
        text="Synthetic organisation",
        order=2,
        source_pages=[5],
    )
    extraction = SectionExtractionResult(sections=[budget_section, ignored_section])
    assessment = AssessorCheckResult(
        extracted_sections=extraction.sections,
        sections=[],
        threshold_flags=[],
    )
    calls = []

    def fake_extract(bundle, settings):
        calls.append("extract")
        return extraction

    def fake_steps(bundle, extracted, settings):
        calls.append("assess")
        assert extracted is extraction
        yield budget_section, 1, 1
        return assessment

    monkeypatch.setattr("backend.app.extract_assessable_sections", fake_extract)
    monkeypatch.setattr("backend.app.iter_assessment_steps", fake_steps)
    pdf = b"%PDF-1.7\ntest"
    files = [
        ("gog", ("gog.pdf", pdf, "application/pdf")),
        ("application_form", ("form.pdf", pdf, "application/pdf")),
        ("grant_application", ("application.pdf", pdf, "application/pdf")),
    ]

    response = asyncio.run(
        post_to_app(
            create_app(make_settings()),
            files=files,
            path="/api/assessor/check/stream",
        )
    )
    events = parse_event_stream(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["content-encoding"] == "identity"
    assert [event["type"] for event in events] == [
        "progress",
        "sections",
        "progress",
        "complete",
    ]
    assert events[0]["phase"] == "extracting"
    assert events[1]["sections"] == [{"id": "budget", "header": "Project budget"}]
    assert events[2] == {
        "type": "progress",
        "phase": "reviewing",
        "section_id": "budget",
        "label": "Reviewing “Project budget”",
        "current": 1,
        "total": 1,
    }
    assert events[3]["result"] == assessment.model_dump(mode="json")
    assert calls == ["extract", "assess"]


def test_assessor_stream_returns_an_error_event_when_extraction_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_extract(bundle, settings):
        raise RuntimeError("Section extraction failed")

    monkeypatch.setattr("backend.app.extract_assessable_sections", fake_extract)
    pdf = b"%PDF-1.7\ntest"
    files = [
        ("gog", ("gog.pdf", pdf, "application/pdf")),
        ("application_form", ("form.pdf", pdf, "application/pdf")),
        ("grant_application", ("application.pdf", pdf, "application/pdf")),
    ]

    response = asyncio.run(
        post_to_app(
            create_app(make_settings()),
            files=files,
            path="/api/assessor/check/stream",
        )
    )
    events = parse_event_stream(response.text)

    assert [event["type"] for event in events] == ["progress", "error"]
    assert "Section extraction failed" in events[1]["message"]


def test_assessor_stream_rejects_non_pdf_content() -> None:
    pdf = b"%PDF-1.7\ntest"
    files = [
        ("gog", ("gog.pdf", b"not a pdf", "application/pdf")),
        ("application_form", ("form.pdf", pdf, "application/pdf")),
        ("grant_application", ("application.pdf", pdf, "application/pdf")),
    ]

    response = asyncio.run(post_to_app(create_app(make_settings()), files=files))

    assert response.status_code == 400
    assert "Selection Criteria (GOG)" in response.json()["detail"]
    assert "valid PDF data" in response.json()["detail"]


def test_writer_stream_reviews_known_fields_without_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = WriterCheckResult(sections=[])
    captured = {}

    def fake_steps(bundle, fields, settings):
        captured["bundle"] = bundle
        ordered = sorted(fields, key=lambda field: field.order)
        yield ordered[0], 1, 2
        yield ordered[1], 2, 2
        return assessment

    monkeypatch.setattr("backend.app.iter_writer_assessment_steps", fake_steps)
    pdf = b"%PDF-1.7\ntest"
    fields = (
        '[{"id":"budget","header":"Budget","type":"budget",'
        '"text":"Other: $1,000","order":2},'
        '{"id":"activity_description","header":"Activity description",'
        '"type":"description","text":"A synthetic activity.","order":1}]'
    )
    files = [
        ("gog", ("gog.pdf", pdf, "application/pdf")),
        ("application_form", ("form.pdf", pdf, "application/pdf")),
        ("fields", (None, fields)),
    ]

    response = asyncio.run(
        post_to_app(
            create_app(make_settings()),
            files=files,
            path="/api/writer/check/stream",
        )
    )
    events = parse_event_stream(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [event["type"] for event in events] == [
        "fields",
        "progress",
        "progress",
        "complete",
    ]
    assert events[0]["fields"] == [
        {"id": "activity_description", "header": "Activity description"},
        {"id": "budget", "header": "Budget"},
    ]
    assert [event.get("phase") for event in events] == [
        None,
        "reviewing",
        "reviewing",
        None,
    ]
    assert events[1]["label"] == "Reviewing “Activity description”"
    assert events[2]["label"] == "Reviewing “Budget”"
    assert not hasattr(captured["bundle"], "grant_application")
