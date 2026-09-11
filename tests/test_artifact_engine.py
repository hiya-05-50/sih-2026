"""Sprint 4 – Artifact Engine Tests.

Tests:
  - DOCX structural validation (opens, has content)
  - XLSX structural validation (opens, required columns present)
  - PDF structural validation (opens, valid header)
  - Semantic validation (required fields populated)
  - Full manifest generation
"""

import pytest
from app.services.artifact_engine import ArtifactEngine
from app.schemas.decision_package import CalculationResult
from app.schemas.evidence import EvidenceObject, NormalizedRegion
from shared.enums import EvidenceType


@pytest.fixture
def engine():
    return ArtifactEngine()


@pytest.fixture
def sample_evidence():
    return [
        EvidenceObject(
            evidence_id="ev-art-001",
            document_id="doc-1",
            source_hash="hash123abc",
            page_number=1,
            region=NormalizedRegion(x=0.1, y=0.1, width=0.8, height=0.2),
            extracted_text="Pressure reading: 4.2 Bar — PASS",
            evidence_type=EvidenceType.KEY_VALUE,
        ),
        EvidenceObject(
            evidence_id="ev-art-002",
            document_id="doc-1",
            source_hash="hash123abc",
            page_number=1,
            region=NormalizedRegion(x=0.1, y=0.4, width=0.8, height=0.3),
            extracted_text="Thermal: 62°C (threshold 65°C) — PASS",
            evidence_type=EvidenceType.TABLE,
        ),
    ]


@pytest.fixture
def sample_calculations():
    return [
        CalculationResult(
            calc_id="calc-art-1",
            parameter_name="pressure_reading",
            primary_result=4.2,
            recomputed_result=4.2,
            results_match=True,
            threshold=5.0,
            threshold_met=True,
            status="PASS",
            evidence_reference="ev-art-001",
            formula_used="measured_pressure",
        ),
        CalculationResult(
            calc_id="calc-art-2",
            parameter_name="thermal_reading",
            primary_result=62.0,
            recomputed_result=62.0,
            results_match=True,
            threshold=65.0,
            threshold_met=True,
            status="PASS",
            evidence_reference="ev-art-002",
            formula_used="measured_temp",
        ),
    ]


class TestDocxGeneration:
    """Test Decision_Note.docx generation."""

    def test_creates_valid_docx(self, engine, sample_evidence, sample_calculations):
        record = engine.create_docx(
            task_id="task-docx-1",
            title="Test Decision Note",
            summary="Test summary for inspection",
            evidence_objects=sample_evidence,
            calculation_results=sample_calculations,
        )
        assert record.filename == "Decision_Note.docx"
        assert record.artifact_type == "DOCX"
        assert record.file_size_bytes > 0
        assert record.content is not None

    def test_structural_validation_passes(self, engine, sample_evidence, sample_calculations):
        record = engine.create_docx(
            task_id="task-docx-2",
            title="Structural Test",
            summary="Testing structure",
            evidence_objects=sample_evidence,
            calculation_results=sample_calculations,
        )
        assert record.structural_valid is True

    def test_semantic_validation_passes(self, engine, sample_evidence, sample_calculations):
        record = engine.create_docx(
            task_id="task-docx-3",
            title="Semantic Test",
            summary="Testing semantics",
            evidence_objects=sample_evidence,
            calculation_results=sample_calculations,
        )
        assert record.semantic_valid is True

    def test_evidence_ids_in_references(self, engine, sample_evidence, sample_calculations):
        record = engine.create_docx(
            task_id="task-docx-4",
            title="Reference Test",
            summary="Test",
            evidence_objects=sample_evidence,
            calculation_results=sample_calculations,
        )
        assert "ev-art-001" in record.evidence_references
        assert "ev-art-002" in record.evidence_references


class TestXlsxGeneration:
    """Test Inspection_Data.xlsx generation."""

    def test_creates_valid_xlsx(self, engine, sample_evidence, sample_calculations):
        record = engine.create_xlsx(
            task_id="task-xlsx-1",
            calculation_results=sample_calculations,
            evidence_objects=sample_evidence,
        )
        assert record.filename == "Inspection_Data.xlsx"
        assert record.artifact_type == "XLSX"
        assert record.file_size_bytes > 0

    def test_structural_validation_passes(self, engine, sample_evidence, sample_calculations):
        record = engine.create_xlsx(
            task_id="task-xlsx-2",
            calculation_results=sample_calculations,
            evidence_objects=sample_evidence,
        )
        assert record.structural_valid is True

    def test_semantic_validation_required_columns(self, engine, sample_evidence, sample_calculations):
        """XLSX must have: measurement, current_value, threshold, status, evidence_reference."""
        record = engine.create_xlsx(
            task_id="task-xlsx-3",
            calculation_results=sample_calculations,
            evidence_objects=sample_evidence,
        )
        assert record.semantic_valid is True

    def test_data_rows_present(self, engine, sample_evidence, sample_calculations):
        record = engine.create_xlsx(
            task_id="task-xlsx-4",
            calculation_results=sample_calculations,
            evidence_objects=sample_evidence,
        )
        # Verify by loading
        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(record.content))
        ws = wb.active
        # Header + 2 data rows
        assert ws.max_row == 3


class TestPdfGeneration:
    """Test Evidence_Report.pdf generation."""

    def test_creates_valid_pdf(self, engine, sample_evidence, sample_calculations):
        record = engine.create_pdf(
            task_id="task-pdf-1",
            evidence_objects=sample_evidence,
            calculation_results=sample_calculations,
        )
        assert record.filename == "Evidence_Report.pdf"
        assert record.artifact_type == "PDF"
        assert record.file_size_bytes > 0

    def test_structural_validation_passes(self, engine, sample_evidence, sample_calculations):
        record = engine.create_pdf(
            task_id="task-pdf-2",
            evidence_objects=sample_evidence,
        )
        assert record.structural_valid is True

    def test_pdf_starts_with_header(self, engine, sample_evidence):
        record = engine.create_pdf(
            task_id="task-pdf-3",
            evidence_objects=sample_evidence,
        )
        assert record.content[:5] == b"%PDF-"


class TestFullManifest:
    """Test full artifact manifest generation."""

    def test_generates_three_artifacts(self, engine, sample_evidence, sample_calculations):
        manifest = engine.generate_full_manifest(
            task_id="task-manifest-1",
            title="Full Manifest Test",
            summary="Testing all three artifacts",
            evidence_objects=sample_evidence,
            calculation_results=sample_calculations,
        )
        assert len(manifest.artifacts) == 3
        filenames = {a.filename for a in manifest.artifacts}
        assert "Decision_Note.docx" in filenames
        assert "Inspection_Data.xlsx" in filenames
        assert "Evidence_Report.pdf" in filenames

    def test_all_valid_flag(self, engine, sample_evidence, sample_calculations):
        manifest = engine.generate_full_manifest(
            task_id="task-manifest-2",
            title="Validation Test",
            summary="Test",
            evidence_objects=sample_evidence,
            calculation_results=sample_calculations,
        )
        assert manifest.all_valid is True
