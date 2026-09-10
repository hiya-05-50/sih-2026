from __future__ import annotations

"""Tests for Evidence Retrieval Index ingestion and querying."""

from app.schemas.evidence import EvidenceObject, NormalizedRegion
from app.services.retrieval_index import EvidenceRetrievalIndex
from shared.enums import EvidenceType


def test_retrieval_index_ingestion_and_search():
    index = EvidenceRetrievalIndex()
    index.clear()

    ev1 = EvidenceObject(
        document_id="doc-A",
        source_hash="hashA"*12,
        page_number=1,
        region=NormalizedRegion(x=0.1, y=0.1, width=0.5, height=0.2),
        extracted_text="Transformer Core thermal threshold optimal",
        confidence=0.98,
        evidence_type=EvidenceType.KEY_VALUE,
    )
    ev2 = EvidenceObject(
        document_id="doc-A",
        source_hash="hashA"*12,
        page_number=1,
        region=NormalizedRegion(x=0.5, y=0.5, width=0.4, height=0.3),
        extracted_text="Official ISO-9001 certification stamp",
        confidence=0.95,
        evidence_type=EvidenceType.STAMP,
    )

    index.ingest_batch([ev1, ev2])

    # Test retrieval by document
    doc_evidence = index.get_by_document("doc-A")
    assert len(doc_evidence) == 2

    # Test search query
    search_results = index.search_evidence("Transformer")
    assert len(search_results) >= 1
    assert search_results[0].evidence_id == ev1.evidence_id
