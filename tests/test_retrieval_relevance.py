"""Sprint 5 – Retrieval Relevance Metric Tests.

Covers:
  - No ground truth → TO BE VALIDATED
  - Perfect retrieval → precision=1, recall=1, MRR=1
  - Partial retrieval → correct intermediate values
  - No relevant results retrieved → precision=0, recall=0, MRR=0
  - MRR calculation for various first-relevant positions
  - Empty retrieved list
  - Integration with SIAB harness field
  - Integration with real EvidenceRetrievalIndex
"""

from __future__ import annotations

import pytest

from app.services.sovereignty.retrieval_relevance import (
    TO_BE_VALIDATED,
    RelevanceGroundTruth,
    RetrievalRelevanceEvaluator,
    RetrievalRelevanceResult,
)


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def evaluator() -> RetrievalRelevanceEvaluator:
    return RetrievalRelevanceEvaluator()


def _gt(query: str, relevant_ids: list[str]) -> RelevanceGroundTruth:
    return RelevanceGroundTruth(query=query, relevant_ids=relevant_ids)


# -----------------------------------------------------------------------
# No ground truth → TO BE VALIDATED
# -----------------------------------------------------------------------


class TestNoGroundTruth:

    def test_none_ground_truth(self, evaluator):
        result = evaluator.evaluate(["id-1", "id-2"], None)
        assert result.precision_at_k == TO_BE_VALIDATED
        assert result.recall_at_k == TO_BE_VALIDATED
        assert result.mrr == TO_BE_VALIDATED

    def test_empty_relevant_ids(self, evaluator):
        gt = _gt("some query", [])
        result = evaluator.evaluate(["id-1"], gt)
        assert result.precision_at_k == TO_BE_VALIDATED
        assert result.recall_at_k == TO_BE_VALIDATED

    def test_total_retrieved_still_counted(self, evaluator):
        result = evaluator.evaluate(["a", "b", "c"], None)
        assert result.total_retrieved == 3


# -----------------------------------------------------------------------
# Perfect retrieval
# -----------------------------------------------------------------------


class TestPerfectRetrieval:

    def test_single_relevant_retrieved(self, evaluator):
        gt = _gt("query", ["id-1"])
        result = evaluator.evaluate(["id-1"], gt)
        assert result.precision_at_k == 1.0
        assert result.recall_at_k == 1.0
        assert result.mrr == 1.0
        assert result.relevant_retrieved == 1

    def test_all_relevant_retrieved(self, evaluator):
        gt = _gt("query", ["a", "b", "c"])
        result = evaluator.evaluate(["a", "b", "c"], gt)
        assert result.precision_at_k == 1.0
        assert result.recall_at_k == 1.0
        assert result.mrr == 1.0
        assert result.relevant_retrieved == 3


# -----------------------------------------------------------------------
# Partial retrieval
# -----------------------------------------------------------------------


class TestPartialRetrieval:

    def test_one_relevant_among_irrelevant(self, evaluator):
        gt = _gt("query", ["a"])
        result = evaluator.evaluate(["x", "a", "y"], gt)
        # precision = 1/3
        assert abs(result.precision_at_k - 0.3333) < 0.001
        assert result.recall_at_k == 1.0
        # MRR = 1/2 (first relevant at rank 2)
        assert result.mrr == 0.5
        assert result.relevant_retrieved == 1

    def test_two_of_three_relevant_retrieved(self, evaluator):
        gt = _gt("query", ["a", "b", "c"])
        result = evaluator.evaluate(["a", "x", "b"], gt)
        # precision = 2/3
        assert abs(result.precision_at_k - 0.6667) < 0.001
        # recall = 2/3
        assert abs(result.recall_at_k - 0.6667) < 0.001
        # MRR = 1/1 (first relevant at rank 1)
        assert result.mrr == 1.0

    def test_retrieved_more_than_relevant(self, evaluator):
        gt = _gt("query", ["a"])
        result = evaluator.evaluate(["a", "b", "c", "d", "e"], gt)
        # precision = 1/5
        assert result.precision_at_k == 0.2
        assert result.recall_at_k == 1.0


# -----------------------------------------------------------------------
# No relevant results found
# -----------------------------------------------------------------------


class TestNoRelevantFound:

    def test_all_irrelevant(self, evaluator):
        gt = _gt("query", ["a", "b"])
        result = evaluator.evaluate(["x", "y", "z"], gt)
        assert result.precision_at_k == 0.0
        assert result.recall_at_k == 0.0
        assert result.mrr == 0.0
        assert result.relevant_retrieved == 0

    def test_empty_retrieved_list(self, evaluator):
        gt = _gt("query", ["a", "b"])
        result = evaluator.evaluate([], gt)
        assert result.precision_at_k == 0.0
        assert result.recall_at_k == 0.0
        assert result.mrr == 0.0
        assert result.k == 0


# -----------------------------------------------------------------------
# MRR edge cases
# -----------------------------------------------------------------------


class TestMRR:

    def test_first_result_relevant(self, evaluator):
        gt = _gt("q", ["a"])
        result = evaluator.evaluate(["a", "b", "c"], gt)
        assert result.mrr == 1.0

    def test_second_result_relevant(self, evaluator):
        gt = _gt("q", ["b"])
        result = evaluator.evaluate(["a", "b", "c"], gt)
        assert result.mrr == 0.5

    def test_third_result_relevant(self, evaluator):
        gt = _gt("q", ["c"])
        result = evaluator.evaluate(["a", "b", "c"], gt)
        assert abs(result.mrr - 0.3333) < 0.001

    def test_fifth_result_relevant(self, evaluator):
        gt = _gt("q", ["e"])
        result = evaluator.evaluate(["a", "b", "c", "d", "e"], gt)
        assert result.mrr == 0.2


# -----------------------------------------------------------------------
# Retrieved relevant IDs tracking
# -----------------------------------------------------------------------


class TestRetrievedTracking:

    def test_tracks_which_ids_matched(self, evaluator):
        gt = _gt("q", ["a", "c"])
        result = evaluator.evaluate(["a", "b", "c", "d"], gt)
        assert "a" in result.retrieved_relevant_ids
        assert "c" in result.retrieved_relevant_ids
        assert "b" not in result.retrieved_relevant_ids


# -----------------------------------------------------------------------
# Integration with real retrieval index
# -----------------------------------------------------------------------


class TestWithRetrievalIndex:
    """Use the actual EvidenceRetrievalIndex to produce retrieved IDs."""

    def test_retrieval_index_relevance(self, evaluator):
        from app.schemas.evidence import EvidenceObject, NormalizedRegion
        from app.services.retrieval_index import EvidenceRetrievalIndex
        from shared.enums import EvidenceType

        index = EvidenceRetrievalIndex()
        index.clear()

        ev1 = EvidenceObject(
            document_id="doc-A",
            source_hash="a" * 64,
            page_number=1,
            region=NormalizedRegion(x=0.1, y=0.1, width=0.5, height=0.2),
            extracted_text="Pressure reading 4.2 Bar threshold met",
            evidence_type=EvidenceType.KEY_VALUE,
        )
        ev2 = EvidenceObject(
            document_id="doc-A",
            source_hash="a" * 64,
            page_number=2,
            region=NormalizedRegion(x=0.1, y=0.1, width=0.5, height=0.2),
            extracted_text="ISO certification stamp verified",
            evidence_type=EvidenceType.STAMP,
        )
        index.ingest_batch([ev1, ev2])

        results = index.search_evidence("pressure", top_k=5)
        retrieved_ids = [r.evidence_id for r in results]

        # ev1 is relevant to "pressure", ev2 is not
        gt = _gt("pressure", [ev1.evidence_id])
        result = evaluator.evaluate(retrieved_ids, gt)

        assert isinstance(result.precision_at_k, float)
        assert isinstance(result.recall_at_k, float)
        assert result.recall_at_k == 1.0  # ev1 should be retrieved
        assert result.relevant_retrieved >= 1


# -----------------------------------------------------------------------
# SIAB harness integration
# -----------------------------------------------------------------------


class TestSIABIntegration:

    def test_siab_metrics_has_retrieval_relevance_field(self):
        from app.services.sovereignty.siab_harness import SIABMetrics

        m = SIABMetrics()
        assert m.retrieval_relevance == TO_BE_VALIDATED

    def test_siab_metrics_accepts_relevance_result(self):
        from app.services.sovereignty.siab_harness import SIABMetrics

        relevance = RetrievalRelevanceResult(
            precision_at_k=0.8,
            recall_at_k=1.0,
            mrr=1.0,
            k=5,
            total_retrieved=5,
            total_relevant=4,
            relevant_retrieved=4,
        )
        m = SIABMetrics(retrieval_relevance=relevance.model_dump())
        assert m.retrieval_relevance["precision_at_k"] == 0.8
        assert m.retrieval_relevance["mrr"] == 1.0
