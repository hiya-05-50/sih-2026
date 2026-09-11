from __future__ import annotations

"""Tests for Document Parser engine and Targeted Vision integration."""

import asyncio
from app.services.document_parser import DocumentParser
from shared.enums import EvidenceType


def test_parse_document_generates_evidence_objects():
    async def _run():
        parser = DocumentParser()
        meta, content = parser.generate_sample_inspection_report("doc-test-100")
        
        response = await parser.parse_document(
            document_id=meta.document_id,
            content=content,
            filename=meta.filename,
            enable_targeted_vision=True,
        )
        
        assert response.document_id == meta.document_id
        assert response.source_hash == meta.sha256_hash
        assert len(response.evidence_objects) >= 5
        
        evidence_types = {ev.evidence_type for ev in response.evidence_objects}
        assert EvidenceType.TABLE in evidence_types
        assert EvidenceType.STAMP in evidence_types
        assert EvidenceType.SIGNATURE in evidence_types

    asyncio.run(_run())


def test_sha256_reproducibility():
    parser = DocumentParser()
    content = b"TEST DOCUMENT CONTENT FOR SHA256"
    hash1 = parser.compute_sha256(content)
    hash2 = parser.compute_sha256(content)
    assert hash1 == hash2
    assert len(hash1) == 64
