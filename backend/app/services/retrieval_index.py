from __future__ import annotations

"""Sprint 2 – Retrieval Index Ingestion Path.

Implements Member D's evidence ingestion path into the retrieval index.
Enables extracted Evidence Objects to be indexed, retrieved by document ID,
and searched by keyword/relevance query.
"""

import logging
from typing import Dict, List, Optional

from app.schemas.evidence import EvidenceObject

logger = logging.getLogger(__name__)


class EvidenceRetrievalIndex:
    """In-memory index for ingesting and retrieving Evidence Objects."""

    def __init__(self) -> None:
        self._index: Dict[str, EvidenceObject] = {}
        self._doc_map: Dict[str, List[str]] = {}  # document_id -> list of evidence_ids

    def ingest_evidence(self, evidence: EvidenceObject) -> bool:
        """Ingest a single Evidence Object into the retrieval index."""
        self._index[evidence.evidence_id] = evidence

        if evidence.document_id not in self._doc_map:
            self._doc_map[evidence.document_id] = []
        if evidence.evidence_id not in self._doc_map[evidence.document_id]:
            self._doc_map[evidence.document_id].append(evidence.evidence_id)

        logger.debug(f"Ingested evidence {evidence.evidence_id} for doc {evidence.document_id}")
        return True

    def ingest_batch(self, evidence_list: List[EvidenceObject]) -> int:
        """Ingest a batch of Evidence Objects. Returns count of ingested items."""
        count = 0
        for item in evidence_list:
            if self.ingest_evidence(item):
                count += 1
        logger.info(f"Batch ingested {count} Evidence Objects into retrieval index")
        return count

    def get_by_document(self, document_id: str) -> List[EvidenceObject]:
        """Retrieve all Evidence Objects for a specific document ID."""
        evidence_ids = self._doc_map.get(document_id, [])
        return [self._index[eid] for eid in evidence_ids if eid in self._index]

    def search_evidence(self, query: str, top_k: int = 5) -> List[EvidenceObject]:
        """Search indexed Evidence Objects by simple term relevance matching."""
        if not query.strip():
            return list(self._index.values())[:top_k]

        query_terms = set(query.lower().split())
        scored_items: List[tuple[float, EvidenceObject]] = []

        for item in self._index.values():
            text_terms = set(item.extracted_text.lower().split())
            type_terms = {item.evidence_type.value.lower()}
            meta_terms = set(str(item.metadata).lower().split())
            all_terms = text_terms | type_terms | meta_terms

            matches = query_terms.intersection(all_terms)
            if matches:
                score = len(matches) / len(query_terms) * item.confidence
                scored_items.append((score, item))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_items[:top_k]]

    def list_all(self) -> List[EvidenceObject]:
        """List all indexed Evidence Objects."""
        return list(self._index.values())

    def clear(self) -> None:
        """Clear all entries from the retrieval index."""
        self._index.clear()
        self._doc_map.clear()
