"""FastAPI entry point for the GOGgles backend."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter, ValidationError

from backend.assessment import (
    SUPPORTED_ASSESSOR_SECTION_IDS,
    extract_assessable_sections,
    iter_assessment_steps,
    iter_applicant_assessment_steps,
)
from backend.config import Settings, get_settings
from backend.documents import (
    AssessorDocumentBundle,
    PdfDocument,
    PdfValidationError,
    ApplicantDocumentBundle,
)
from backend.models import HealthResponse, ApplicantDraftField

_APPLICANT_FIELDS_ADAPTER = TypeAdapter(list[ApplicantDraftField])
_LOGGER = logging.getLogger(__name__)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_NAIDOC_ROOT = _PROJECT_ROOT / "demo" / "naidoc"
_NAIDOC_DOCUMENTS = _NAIDOC_ROOT / "documents"
_NAIDOC_TEST_PDFS = _NAIDOC_ROOT / "test-cases" / "pdf"
_DEMO_FILES = {
    "gog": _NAIDOC_DOCUMENTS
    / ("NAIDOC 2026 Local Grants Opportunity - Grant Opportunity Guidelines.pdf"),
    "application_form": _NAIDOC_DOCUMENTS
    / ("NAIDOC 2026 - Sample Application Form.pdf"),
    "applicants_guide": _NAIDOC_DOCUMENTS
    / ("NAIDOC 2026 Local Grants - Applicants Guide.pdf"),
    **{
        f"application_{number:02d}": _NAIDOC_TEST_PDFS
        / f"synthetic-application-{number:02d}.pdf"
        for number in range(1, 7)
    },
}


async def _read_pdf(upload: UploadFile, label: str) -> PdfDocument:
    """Read and validate one uploaded PDF without saving it."""

    filename = upload.filename or f"{label}.pdf"
    content = await upload.read()
    try:
        return PdfDocument(label=label, filename=filename, content=content)
    except PdfValidationError as exc:
        raise HTTPException(status_code=400, detail=f"{label}: {exc}") from None


async def _build_assessor_bundle(
    gog: UploadFile,
    application_form: UploadFile,
    grant_application: UploadFile,
    supporting_documents: list[UploadFile] | None,
) -> AssessorDocumentBundle:
    """Build the labelled four-box bundle in memory."""

    return AssessorDocumentBundle(
        gog=await _read_pdf(gog, "Selection Criteria (GOG)"),
        application_form=await _read_pdf(application_form, "Application Form"),
        supporting_documents=tuple(
            [
                await _read_pdf(document, "Supporting Document")
                for document in supporting_documents or []
            ]
        ),
        grant_application=await _read_pdf(
            grant_application,
            "Grant Application",
        ),
    )


async def _build_applicant_bundle(
    gog: UploadFile,
    application_form: UploadFile,
    supporting_documents: list[UploadFile] | None,
) -> ApplicantDocumentBundle:
    """Build an applicant-facing bundle that cannot contain a proposal."""

    return ApplicantDocumentBundle(
        gog=await _read_pdf(gog, "Selection Criteria (GOG)"),
        application_form=await _read_pdf(application_form, "Application Form"),
        supporting_documents=tuple(
            [
                await _read_pdf(document, "Supporting Document")
                for document in supporting_documents or []
            ]
        ),
    )


_STREAM_COMPLETE = object()


def _progress_event(event: dict) -> str:
    """Encode one progress update as a server-sent event."""

    return f"data: {json.dumps(event, separators=(',', ':'))}\n\n"


def _stream_error_event(exc: Exception) -> dict[str, str]:
    """Return a concise error event for a stream that has already started."""

    detail = str(exc).strip()
    message = "The check could not be completed."
    if detail:
        message = f"{message} {detail}"
    return {"type": "error", "message": message}


def _streaming_response(
    *,
    run_check: Callable[[], None],
    event_queue: Queue[dict | object],
    stop_requested: Event,
    thread_name: str,
) -> StreamingResponse:
    """Run one blocking check in a thread and stream its queued events."""

    async def events() -> AsyncIterator[str]:
        worker = Thread(target=run_check, name=thread_name, daemon=True)
        worker.start()
        try:
            while True:
                try:
                    event = event_queue.get_nowait()
                except Empty:
                    await asyncio.sleep(0.05)
                    continue
                if event is _STREAM_COMPLETE:
                    break
                yield _progress_event(event)
        finally:
            stop_requested.set()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Content-Encoding": "identity",
            "X-Accel-Buffering": "no",
        },
    )


def _validated_applicant_fields(fields: str) -> list[ApplicantDraftField]:
    """Validate the submitted isolated applicant fields for both applicant routes."""

    try:
        draft_fields = _APPLICANT_FIELDS_ADAPTER.validate_json(fields)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Fields must be a valid JSON array of draft fields.",
        ) from exc
    if not draft_fields:
        raise HTTPException(
            status_code=422,
            detail="At least one draft field is required.",
        )
    return draft_fields


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API, allowing tests to inject harmless settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Uvicorn does not configure application loggers, so without this the
        # INFO-level cache-usage lines from backend.assessment never appear.
        logging.basicConfig(level=logging.INFO)
        app.state.settings = settings or get_settings()
        yield

    application = FastAPI(
        title="GOGgles IM2026 API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @application.get(
        "/api/demo/files/{key}",
        response_class=FileResponse,
        summary="Load a public or synthetic NAIDOC demo PDF",
    )
    async def demo_file(key: str) -> FileResponse:
        path = _DEMO_FILES.get(key)
        if path is None:
            raise HTTPException(status_code=404, detail="Demo document not found.")
        return FileResponse(
            path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{path.name}"',
            },
        )

    @application.post(
        "/api/assessor/check/stream",
        summary="Run assessor checks with live progress",
    )
    async def assessor_check_stream(
        request: Request,
        gog: Annotated[UploadFile, File(description="Selection Criteria (GOG) PDF")],
        application_form: Annotated[
            UploadFile,
            File(description="Application Form PDF"),
        ],
        grant_application: Annotated[
            UploadFile,
            File(description="Submitted Grant Application PDF"),
        ],
        supporting_documents: Annotated[
            list[UploadFile] | None,
            File(description="Optional applicant-facing supporting PDFs"),
        ] = None,
    ) -> StreamingResponse:
        """Stream real pass-one and per-section progress, then the final result."""

        bundle = await _build_assessor_bundle(
            gog,
            application_form,
            grant_application,
            supporting_documents,
        )
        settings = request.app.state.settings
        event_queue: Queue[dict | object] = Queue()
        stop_requested = Event()

        def run_check() -> None:
            try:
                event_queue.put(
                    {
                        "type": "progress",
                        "phase": "extracting",
                        "label": "Extracting assessable sections",
                    }
                )
                extraction = extract_assessable_sections(bundle, settings)
                if stop_requested.is_set():
                    return
                reviewable_sections = [
                    section
                    for section in extraction.sections
                    if section.id in SUPPORTED_ASSESSOR_SECTION_IDS
                ]
                event_queue.put(
                    {
                        "type": "sections",
                        "sections": [
                            {"id": section.id, "header": section.header}
                            for section in reviewable_sections
                        ],
                    }
                )

                steps = iter_assessment_steps(bundle, extraction, settings)
                while not stop_requested.is_set():
                    try:
                        section, current, total = next(steps)
                    except StopIteration as completed:
                        result = completed.value
                        break
                    if stop_requested.is_set():
                        return
                    event_queue.put(
                        {
                            "type": "progress",
                            "phase": "reviewing",
                            "section_id": section.id,
                            "label": f"Reviewing “{section.header}”",
                            "current": current,
                            "total": total,
                        }
                    )

                else:
                    return

                event_queue.put(
                    {
                        "type": "complete",
                        "result": result.model_dump(mode="json"),
                    }
                )
            except Exception as exc:
                _LOGGER.exception("Streamed assessor check failed")
                event_queue.put(_stream_error_event(exc))
            finally:
                event_queue.put(_STREAM_COMPLETE)

        return _streaming_response(
            run_check=run_check,
            event_queue=event_queue,
            stop_requested=stop_requested,
            thread_name="assessor-progress",
        )

    @application.post(
        "/api/applicant/check/stream",
        summary="Check isolated applicant fields with live progress",
    )
    async def applicant_check_stream(
        request: Request,
        gog: Annotated[UploadFile, File(description="Selection Criteria (GOG) PDF")],
        application_form: Annotated[
            UploadFile,
            File(description="Application Form PDF"),
        ],
        fields: Annotated[
            str,
            Form(description="JSON array of isolated applicant draft fields"),
        ],
        supporting_documents: Annotated[
            list[UploadFile] | None,
            File(description="Optional applicant-facing supporting PDFs"),
        ] = None,
    ) -> StreamingResponse:
        """Stream one real progress stage for each submitted applicant field."""

        draft_fields = _validated_applicant_fields(fields)
        bundle = await _build_applicant_bundle(
            gog,
            application_form,
            supporting_documents,
        )
        settings = request.app.state.settings
        event_queue: Queue[dict | object] = Queue()
        stop_requested = Event()

        def run_check() -> None:
            try:
                ordered_fields = sorted(draft_fields, key=lambda item: item.order)
                event_queue.put(
                    {
                        "type": "fields",
                        "fields": [
                            {"id": field.id, "header": field.header}
                            for field in ordered_fields
                        ],
                    }
                )
                steps = iter_applicant_assessment_steps(bundle, draft_fields, settings)
                while not stop_requested.is_set():
                    try:
                        field, current, total = next(steps)
                    except StopIteration as completed:
                        result = completed.value
                        break
                    if stop_requested.is_set():
                        return
                    event_queue.put(
                        {
                            "type": "progress",
                            "phase": "reviewing",
                            "field_id": field.id,
                            "label": f"Reviewing “{field.header}”",
                            "current": current,
                            "total": total,
                        }
                    )
                else:
                    return

                event_queue.put(
                    {
                        "type": "complete",
                        "result": result.model_dump(mode="json"),
                    }
                )
            except Exception as exc:
                _LOGGER.exception("Streamed applicant check failed")
                event_queue.put(_stream_error_event(exc))
            finally:
                event_queue.put(_STREAM_COMPLETE)

        return _streaming_response(
            run_check=run_check,
            event_queue=event_queue,
            stop_requested=stop_requested,
            thread_name="applicant-progress",
        )

    frontend_dist = _PROJECT_ROOT / "frontend/dist"
    if frontend_dist.is_dir():

        @application.get("/how-it-works", include_in_schema=False)
        @application.get("/how-it-works/", include_in_schema=False)
        @application.get("/example-results", include_in_schema=False)
        @application.get("/example-results/", include_in_schema=False)
        @application.get("/for-devs", include_in_schema=False)
        @application.get("/for-devs/", include_in_schema=False)
        async def frontend_page() -> FileResponse:
            """Serve standalone React pages at their clean direct URLs."""

            return FileResponse(
                frontend_dist / "index.html",
                media_type="text/html",
            )

        application.mount(
            "/",
            StaticFiles(directory=frontend_dist, html=True),
            name="frontend",
        )

    return application


app = create_app()
