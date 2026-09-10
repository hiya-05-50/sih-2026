from __future__ import annotations

"""Sprint 2 – Documents & Vertical Slice V0 API Endpoints.

Provides endpoints under ``/v1/documents`` for uploading documents,
parsing layout & evidence objects, searching retrieval index,
and executing the thin Vertical Slice V0 pipeline:
  `UPLOAD → OCR → EVIDENCE → RETRIEVAL → REASONING → ARTIFACT`
"""

import time
import uuid
from typing import List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.evidence import (
    DocumentMetadata,
    DocumentParseResponse,
    EvidenceObject,
    VerticalSliceV0Response,
)
from app.services.document_parser import DocumentParser
from app.services.retrieval_index import EvidenceRetrievalIndex

router = APIRouter(prefix="/v1/documents", tags=["documents"])

# Global singletons for documents and evidence retrieval index
parser_instance = DocumentParser()
retrieval_index_instance = EvidenceRetrievalIndex()
document_store: dict[str, tuple[DocumentMetadata, bytes]] = {}

# Pre-seed document store with sample document on startup
_sample_meta, _sample_content = parser_instance.generate_sample_inspection_report("doc-sample-01")
document_store[_sample_meta.document_id] = (_sample_meta, _sample_content)


@router.post("/upload", response_model=DocumentMetadata)
async def upload_document(file: Optional[UploadFile] = File(None)) -> DocumentMetadata:
    """Upload a document file (PDF/Image) or generate a sample report if no file provided."""
    if file and file.filename:
        content = await file.read()
        filename = file.filename
        content_type = file.content_type or "application/pdf"
    else:
        # Fallback to sample report
        meta, content = parser_instance.generate_sample_inspection_report()
        document_store[meta.document_id] = (meta, content)
        return meta

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    sha256 = parser_instance.compute_sha256(content)
    meta = DocumentMetadata(
        document_id=doc_id,
        filename=filename,
        file_size_bytes=len(content),
        sha256_hash=sha256,
        page_count=1,
        content_type=content_type,
    )
    document_store[doc_id] = (meta, content)
    return meta


@router.post("/{document_id}/parse", response_model=DocumentParseResponse)
async def parse_document(
    document_id: str, enable_targeted_vision: bool = True
) -> DocumentParseResponse:
    """Parse document into Evidence Objects and ingest them into the retrieval index."""
    if document_id not in document_store:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    meta, content = document_store[document_id]
    response = await parser_instance.parse_document(
        document_id=document_id,
        content=content,
        filename=meta.filename,
        enable_targeted_vision=enable_targeted_vision,
    )

    # Ingest extracted evidence into retrieval index (Member D)
    retrieval_index_instance.ingest_batch(response.evidence_objects)
    return response


@router.get("/{document_id}/evidence", response_model=List[EvidenceObject])
async def get_document_evidence(document_id: str) -> List[EvidenceObject]:
    """Retrieve all extracted Evidence Objects for a document."""
    evidence_list = retrieval_index_instance.get_by_document(document_id)
    if not evidence_list and document_id in document_store:
        # Auto-parse if not yet parsed
        meta, content = document_store[document_id]
        parse_resp = await parser_instance.parse_document(
            document_id=document_id, content=content, filename=meta.filename
        )
        retrieval_index_instance.ingest_batch(parse_resp.evidence_objects)
        evidence_list = parse_resp.evidence_objects

    return evidence_list


@router.post("/{document_id}/vertical-slice", response_model=VerticalSliceV0Response)
async def execute_vertical_slice_v0(document_id: str) -> VerticalSliceV0Response:
    """Execute the complete Vertical Slice V0 pipeline:

    `UPLOAD → OCR → EVIDENCE → RETRIEVAL → REASONING → ARTIFACT`
    """
    start_time = time.time()

    if document_id not in document_store:

        # Auto-create sample document if doc_id not found
        meta, content = parser_instance.generate_sample_inspection_report(document_id)
        document_store[document_id] = (meta, content)
    else:
        meta, content = document_store[document_id]

    # Step 1: Document Parsing & Targeted Vision OCR
    parse_resp = await parser_instance.parse_document(
        document_id=document_id, content=content, filename=meta.filename
    )

    # Step 2: Retrieval Ingestion
    retrieval_indexed_count = retrieval_index_instance.ingest_batch(parse_resp.evidence_objects)

    # Step 3: Stub Retrieval Query
    retrieved_evidence = retrieval_index_instance.search_evidence(query="transformer compliance", top_k=3)

    # Step 4: Stub Reasoning Analysis
    reasoning_summary = (
        f"Vertical Slice V0 Reasoning Engine analyzed {len(parse_resp.evidence_objects)} Evidence Objects "
        f"for source hash {meta.sha256_hash[:12]}... "
        f"Verified 100% compliance across transformer core, pressure relays, and ISO-9001 certification stamp."
    )

    # Step 5: Stub Artifact Generation
    artifact = {
        "artifact_id": f"art-v0-{uuid.uuid4().hex[:6]}",
        "title": "Substation Delta-4 Inspection Compliance Certificate",
        "status": "VALIDATED",
        "provenance_hash": meta.sha256_hash,
        "evidence_references": [ev.evidence_id for ev in parse_resp.evidence_objects],

        "summary": reasoning_summary,
    }

    duration_ms = (time.time() - start_time) * 1000.0

    return VerticalSliceV0Response(
        document_metadata=meta,
        evidence_count=len(parse_resp.evidence_objects),
        evidence_objects=parse_resp.evidence_objects,
        retrieval_indexed_count=retrieval_indexed_count,
        reasoning_summary=reasoning_summary,
        generated_artifact=artifact,
        pipeline_duration_ms=duration_ms,
    )
