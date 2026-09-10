from __future__ import annotations

"""Tests for Evidence Object schema, Normalized Region, and SHA-256 hashing."""

import pytest
from pydantic import ValidationError

from app.schemas.evidence import EvidenceObject, NormalizedRegion
from shared.enums import EvidenceType


def test_normalized_region_valid():
    region = NormalizedRegion(x=0.1, y=0.2, width=0.5, height=0.3)
    assert region.x == 0.1
    assert region.y == 0.2
    assert region.width == 0.5
    assert region.height == 0.3


def test_normalized_region_invalid_range():
    with pytest.raises(ValidationError):
        NormalizedRegion(x=-0.1, y=0.2, width=0.5, height=0.3)

    with pytest.raises(ValidationError):
        NormalizedRegion(x=0.1, y=1.2, width=0.5, height=0.3)


def test_evidence_object_instantiation():
    evidence = EvidenceObject(
        document_id="doc-123",
        source_hash="a"*64,
        page_number=1,
        region=NormalizedRegion(x=0.08, y=0.38, width=0.84, height=0.25),
        extracted_text="Compliance Table Content",
        confidence=0.95,
        evidence_type=EvidenceType.TABLE,
        metadata={"section": "table_1"},
    )
    assert evidence.evidence_id.startswith("ev-")
    assert evidence.document_id == "doc-123"
    assert len(evidence.source_hash) == 64
    assert evidence.evidence_type == EvidenceType.TABLE
    assert evidence.confidence == 0.95
