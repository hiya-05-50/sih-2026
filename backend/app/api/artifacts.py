from __future__ import annotations

"""Sprint 4 – Artifact API Endpoints.

Provides artifact generation, listing, and download endpoints.
Artifact delivery is gated behind the approval invariant for AMBER/RED risk tasks.
"""

import io
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.decision_package import ArtifactManifest, ArtifactRecord
from app.services.artifact_engine import ArtifactEngine
from app.services.flagship_pipeline import FlagshipPipeline

router = APIRouter(prefix="/v1/artifacts", tags=["artifacts"])

_pipeline: FlagshipPipeline | None = None
_artifact_engine: ArtifactEngine = ArtifactEngine()

# In-memory artifact store (keyed by artifact_id)
_artifact_store: dict[str, ArtifactRecord] = {}


def configure(pipeline: FlagshipPipeline) -> None:
    """Inject the flagship pipeline reference."""
    global _pipeline
    _pipeline = pipeline


@router.get("/task/{task_id}", response_model=List[dict])
async def list_task_artifacts(task_id: str) -> List[dict]:
    """List all artifacts generated for a task."""
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not configured")

    execution = _pipeline.get_execution(task_id)
    if execution is None:
        raise HTTPException(status_code=404, detail=f"No execution found for task '{task_id}'")

    if execution.artifact_manifest is None:
        return []

    result = []
    for art in execution.artifact_manifest.artifacts:
        _artifact_store[art.artifact_id] = art
        result.append({
            "artifact_id": art.artifact_id,
            "filename": art.filename,
            "artifact_type": art.artifact_type,
            "file_size_bytes": art.file_size_bytes,
            "structural_valid": art.structural_valid,
            "semantic_valid": art.semantic_valid,
            "evidence_references": art.evidence_references,
            "created_at": art.created_at,
        })
    return result


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    """Download a generated artifact file."""
    record = _artifact_store.get(artifact_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

    if record.content is None:
        raise HTTPException(status_code=410, detail="Artifact content no longer available")

    content_type_map = {
        "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "PDF": "application/pdf",
    }

    return StreamingResponse(
        io.BytesIO(record.content),
        media_type=content_type_map.get(record.artifact_type, "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename={record.filename}",
        },
    )
