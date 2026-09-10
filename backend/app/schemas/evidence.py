from __future__ import annotations

"""Sprint 2 – Evidence Object & Document Schemas.

Defines the frozen Evidence Object schema, Normalized Region (0.0 - 1.0 bounding box),
source hashing (SHA-256 provenance), and Vertical Slice V0 execution contracts.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from shared.enums import EvidenceType


class NormalizedRegion(BaseModel):
    """Normalized bounding box coordinates relative to page dimensions [0.0, 1.0]."""

    x: float = Field(..., ge=0.0, le=1.0, description="Normalized X coordinate of top-left corner")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized Y coordinate of top-left corner")
    width: float = Field(..., ge=0.0, le=1.0, description="Normalized width of region")
    height: float = Field(..., ge=0.0, le=1.0, description="Normalized height of region")

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


class EvidenceObject(BaseModel):
    """Canonical Evidence Object representation per Master PRD §16."""

    evidence_id: str = Field(
        default_factory=lambda: f"ev-{uuid.uuid4().hex[:12]}",
        description="Unique identifier for the evidence item",
    )
    document_id: str = Field(..., description="ID of the parent source document")
    source_hash: str = Field(..., description="SHA-256 cryptographic hash of source page/content")
    page_number: int = Field(..., ge=1, description="1-based page number within the document")
    region: NormalizedRegion = Field(..., description="Normalized bounding box location")
    extracted_text: str = Field(..., description="Extracted OCR or vision model text content")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score of extraction"
    )
    evidence_type: EvidenceType = Field(
        default=EvidenceType.TEXT_BLOCK, description="Type of evidence region"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provenance metadata (e.g. vision rationale, table rows, stamp type)",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )


class DocumentMetadata(BaseModel):
    """Metadata for an uploaded or ingested document."""

    document_id: str = Field(..., description="Unique document ID")
    filename: str = Field(..., description="Original filename")
    file_size_bytes: int = Field(..., description="Size of file in bytes")
    sha256_hash: str = Field(..., description="SHA-256 hash of full file content")
    page_count: int = Field(default=1, ge=1, description="Total pages")
    content_type: str = Field(default="application/pdf", description="MIME type")
    uploaded_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DocumentParseRequest(BaseModel):
    """Request to parse a document and extract Evidence Objects."""

    document_id: str
    enable_targeted_vision: bool = Field(
        default=True, description="Enable targeted vision model calls on complex pages"
    )


class DocumentParseResponse(BaseModel):
    """Response containing extracted Evidence Objects."""

    document_id: str
    source_hash: str
    total_pages: int
    evidence_objects: List[EvidenceObject]
    parsed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VerticalSliceV0Response(BaseModel):
    """Complete response for Vertical Slice V0 pipeline execution."""

    execution_id: str = Field(default_factory=lambda: f"v0-{uuid.uuid4().hex[:8]}")
    document_metadata: DocumentMetadata
    evidence_count: int
    evidence_objects: List[EvidenceObject]
    retrieval_indexed_count: int
    reasoning_summary: str
    generated_artifact: Dict[str, Any]
    pipeline_duration_ms: float
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
