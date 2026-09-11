from __future__ import annotations

"""Sprint 7 – Traceability API.

Exposes the formal PRD §41 traceability sign-off as a REST endpoint.
"""

from fastapi import APIRouter

from app.services.traceability import TraceabilityReport, TraceabilityService

router = APIRouter(prefix="/v1/traceability", tags=["traceability"])

_service: TraceabilityService | None = None


def configure(service: TraceabilityService) -> None:
    """Inject the traceability service."""
    global _service
    _service = service


@router.get("/signoff", response_model=TraceabilityReport)
def get_traceability_signoff() -> TraceabilityReport:
    """Generate and return the formal traceability sign-off report.

    Maps all 13 PS requirements (R1–R13) to implementation evidence,
    test evidence, and judge demo step numbers.
    """
    assert _service is not None, "TraceabilityService not configured"
    return _service.generate_report()
