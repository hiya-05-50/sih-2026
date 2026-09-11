"""Sprint 5 – Evidence Quality Metrics Tests.

Covers:
  - Precision / recall / F1 calculation with known ground truth
  - Perfect extraction → precision=1, recall=1, F1=1
  - Partial extraction → correct intermediate values
  - No ground truth → all metrics are "TO BE VALIDATED"
  - Empty extracted list with ground truth → recall=0
  - Text-fragment matching
  - Integration with real EvidenceObject from the parser
  - SIAB harness field exists for evidence_quality
"""

from __future__ import annotations

import pytest

from app.services.sovereignty.evidence_quality import (
    TO_BE_VALIDATED,
    EvidenceQualityEvaluator,
    EvidenceQualityResult,
    GroundTruthAnnotation,
)
from shared.enums import EvidenceType


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


@pytest.fixture
def evaluator() -> EvidenceQualityEvaluator:
    return EvidenceQualityEvaluator()


def _make_evidence(evidence_type: EvidenceType, text: str = ""):
    """Lightweight evidence-like object for testing."""
    from app.schemas.evidence import EvidenceObject, NormalizedRegion

    return EvidenceObject(
        document_id="doc-test",
        source_hash="a" * 64,
        page_number=1,
        region=NormalizedRegion(x=0.0, y=0.0, width=1.0, height=1.0),
        extracted_text=text,
        evidence_type=evidence_type,
    )


def _make_annotation(
    label: str,
    evidence_type: EvidenceType,
    text_fragment: str | None = None,
) -> GroundTruthAnnotation:
    return GroundTruthAnnotation(
        label=label,
        evidence_type=evidence_type,
        expected_text_fragment=text_fragment,
    )


# -----------------------------------------------------------------------
# No ground truth → TO BE VALIDATED
# -----------------------------------------------------------------------


class TestNoGroundTruth:
    """When no annotations exist, metrics must be TO BE VALIDATED."""

    def test_none_ground_truth(self, evaluator):
        extracted = [_make_evidence(EvidenceType.TABLE)]
        result = evaluator.evaluate(extracted, None)
        assert result.precision == TO_BE_VALIDATED
        assert result.recall == TO_BE_VALIDATED
        assert result.f1_score == TO_BE_VALIDATED

    def test_empty_ground_truth(self, evaluator):
        extracted = [_make_evidence(EvidenceType.TABLE)]
        result = evaluator.evaluate(extracted, [])
        assert result.precision == TO_BE_VALIDATED
        assert result.recall == TO_BE_VALIDATED
        assert result.f1_score == TO_BE_VALIDATED

    def test_total_extracted_still_counted(self, evaluator):
        extracted = [
            _make_evidence(EvidenceType.TABLE),
            _make_evidence(EvidenceType.STAMP),
        ]
        result = evaluator.evaluate(extracted, None)
        assert result.total_extracted == 2
        assert result.total_ground_truth == 0


# -----------------------------------------------------------------------
# Perfect extraction
# -----------------------------------------------------------------------


class TestPerfectExtraction:
    """When extraction matches ground truth perfectly."""

    def test_single_item_perfect(self, evaluator):
        extracted = [_make_evidence(EvidenceType.TABLE, "Pressure: 4.2")]
        annotations = [_make_annotation("pressure", EvidenceType.TABLE)]
        result = evaluator.evaluate(extracted, annotations)
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.f1_score == 1.0
        assert result.true_positives == 1
        assert result.false_positives == 0
        assert result.false_negatives == 0

    def test_multiple_items_perfect(self, evaluator):
        extracted = [
            _make_evidence(EvidenceType.TABLE, "Pressure data"),
            _make_evidence(EvidenceType.STAMP, "ISO cert"),
            _make_evidence(EvidenceType.SIGNATURE, "Inspector sig"),
        ]
        annotations = [
            _make_annotation("pressure", EvidenceType.TABLE),
            _make_annotation("certification", EvidenceType.STAMP),
            _make_annotation("signature", EvidenceType.SIGNATURE),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.f1_score == 1.0
        assert result.true_positives == 3


# -----------------------------------------------------------------------
# Partial extraction
# -----------------------------------------------------------------------


class TestPartialExtraction:
    """Extraction finds some but not all ground truth items."""

    def test_one_of_two_found(self, evaluator):
        extracted = [_make_evidence(EvidenceType.TABLE)]
        annotations = [
            _make_annotation("pressure", EvidenceType.TABLE),
            _make_annotation("signature", EvidenceType.SIGNATURE),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert result.true_positives == 1
        assert result.false_negatives == 1
        assert result.false_positives == 0
        assert result.recall == 0.5
        assert result.precision == 1.0
        # F1 = 2 * 1.0 * 0.5 / (1.0 + 0.5) = 2/3
        assert abs(result.f1_score - 0.6667) < 0.001

    def test_extra_extracted_items(self, evaluator):
        """More extracted than ground truth → lower precision."""
        extracted = [
            _make_evidence(EvidenceType.TABLE),
            _make_evidence(EvidenceType.KEY_VALUE),
            _make_evidence(EvidenceType.STAMP),
        ]
        annotations = [
            _make_annotation("pressure", EvidenceType.TABLE),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert result.true_positives == 1
        assert result.false_positives == 2
        assert result.false_negatives == 0
        assert result.recall == 1.0
        # precision = 1/3
        assert abs(result.precision - 0.3333) < 0.001

    def test_no_matches_at_all(self, evaluator):
        extracted = [_make_evidence(EvidenceType.KEY_VALUE)]
        annotations = [
            _make_annotation("signature", EvidenceType.SIGNATURE),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert result.true_positives == 0
        assert result.false_positives == 1
        assert result.false_negatives == 1
        assert result.precision == 0.0
        assert result.recall == 0.0
        assert result.f1_score == 0.0


# -----------------------------------------------------------------------
# Empty extracted list
# -----------------------------------------------------------------------


class TestEmptyExtracted:
    """Nothing extracted but ground truth exists."""

    def test_empty_extraction_with_ground_truth(self, evaluator):
        annotations = [
            _make_annotation("pressure", EvidenceType.TABLE),
            _make_annotation("signature", EvidenceType.SIGNATURE),
        ]
        result = evaluator.evaluate([], annotations)
        assert result.recall == 0.0
        assert result.precision == 0.0
        assert result.f1_score == 0.0
        assert result.false_negatives == 2
        assert result.total_extracted == 0

    def test_both_empty(self, evaluator):
        result = evaluator.evaluate([], [])
        assert result.precision == TO_BE_VALIDATED


# -----------------------------------------------------------------------
# Text-fragment matching
# -----------------------------------------------------------------------


class TestTextFragmentMatching:
    """When annotations include expected text fragments."""

    def test_text_fragment_match(self, evaluator):
        extracted = [
            _make_evidence(EvidenceType.TABLE, "Pressure: 4.2 Bar"),
        ]
        annotations = [
            _make_annotation("pressure", EvidenceType.TABLE, "4.2 Bar"),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert result.true_positives == 1
        assert result.recall == 1.0

    def test_text_fragment_mismatch(self, evaluator):
        """Right type but wrong text fragment → no match."""
        extracted = [
            _make_evidence(EvidenceType.TABLE, "Temperature: 62C"),
        ]
        annotations = [
            _make_annotation("pressure", EvidenceType.TABLE, "4.2 Bar"),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert result.true_positives == 0
        assert result.false_negatives == 1

    def test_case_insensitive_fragment(self, evaluator):
        extracted = [
            _make_evidence(EvidenceType.KEY_VALUE, "PASS - All Clear"),
        ]
        annotations = [
            _make_annotation("status", EvidenceType.KEY_VALUE, "pass"),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert result.true_positives == 1

    def test_no_fragment_matches_any_text(self, evaluator):
        """Annotation without text fragment matches on type alone."""
        extracted = [
            _make_evidence(EvidenceType.STAMP, "anything at all"),
        ]
        annotations = [
            _make_annotation("cert_stamp", EvidenceType.STAMP),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert result.true_positives == 1


# -----------------------------------------------------------------------
# Integration: real evidence objects from parser
# -----------------------------------------------------------------------


class TestWithRealEvidence:
    """Use the document parser to produce evidence, then evaluate."""

    def test_parser_evidence_against_annotations(self, evaluator):
        """Evaluate evidence from the sample inspection report."""
        import asyncio
        from app.services.document_parser import DocumentParser

        parser = DocumentParser()
        meta, content = parser.generate_sample_inspection_report("doc-eq-1")
        response = asyncio.run(
            parser.parse_document(
                document_id=meta.document_id,
                content=content,
                filename=meta.filename,
                enable_targeted_vision=True,
            )
        )

        # Build annotations matching what the sample report produces
        annotations = [
            _make_annotation("table_data", EvidenceType.TABLE),
            _make_annotation("stamp", EvidenceType.STAMP),
            _make_annotation("signature", EvidenceType.SIGNATURE),
        ]

        result = evaluator.evaluate(response.evidence_objects, annotations)
        # The sample report should produce these types
        assert result.recall == 1.0
        assert result.true_positives == 3
        assert isinstance(result.precision, float)
        assert isinstance(result.f1_score, float)


# -----------------------------------------------------------------------
# SIAB harness integration field
# -----------------------------------------------------------------------


class TestSIABIntegration:
    """The SIAB harness metrics model includes evidence_quality."""

    def test_siab_metrics_has_evidence_quality_field(self):
        from app.services.sovereignty.siab_harness import SIABMetrics

        m = SIABMetrics()
        assert m.evidence_quality == TO_BE_VALIDATED

    def test_siab_metrics_accepts_quality_result(self):
        from app.services.sovereignty.siab_harness import SIABMetrics

        quality = EvidenceQualityResult(
            precision=0.85, recall=0.9, f1_score=0.87,
            true_positives=9, false_positives=2, false_negatives=1,
            total_extracted=11, total_ground_truth=10,
        )
        m = SIABMetrics(evidence_quality=quality.model_dump())
        assert m.evidence_quality["precision"] == 0.85


# -----------------------------------------------------------------------
# Matched / unmatched label tracking
# -----------------------------------------------------------------------


class TestLabelTracking:
    """Evaluator tracks which ground-truth labels matched."""

    def test_matched_labels_reported(self, evaluator):
        extracted = [_make_evidence(EvidenceType.TABLE)]
        annotations = [
            _make_annotation("pressure", EvidenceType.TABLE),
            _make_annotation("signature", EvidenceType.SIGNATURE),
        ]
        result = evaluator.evaluate(extracted, annotations)
        assert "pressure" in result.matched_labels
        assert "signature" in result.unmatched_labels
