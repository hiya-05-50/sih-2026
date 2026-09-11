"""Sprint 4 – Deterministic Compute Engine Tests.

Tests:
  - Real vibration threshold calculation
  - Independent recomputation matches
  - Tolerance comparison (exact + percentage)
  - Formula evaluation with math functions
  - Batch execution
  - Flagship inspection calculation builder
"""

import pytest
from app.services.deterministic_compute import DeterministicComputeEngine
from app.schemas.decision_package import CalculationRequest


@pytest.fixture
def engine():
    return DeterministicComputeEngine()


class TestFormulaEvaluation:
    """Test the restricted formula evaluation engine."""

    def test_simple_arithmetic(self, engine):
        result = engine._evaluate_formula("a + b", {"a": 3.0, "b": 4.0})
        assert result == 7.0

    def test_multiplication(self, engine):
        result = engine._evaluate_formula("a * b", {"a": 2.5, "b": 4.0})
        assert result == 10.0

    def test_sqrt_function(self, engine):
        result = engine._evaluate_formula("sqrt(x)", {"x": 16.0})
        assert result == 4.0

    def test_complex_formula(self, engine):
        result = engine._evaluate_formula(
            "sqrt(x**2 + y**2)", {"x": 3.0, "y": 4.0}
        )
        assert abs(result - 5.0) < 1e-10

    def test_invalid_formula_raises(self, engine):
        with pytest.raises(ValueError, match="Formula evaluation failed"):
            engine._evaluate_formula("import os", {})


class TestToleranceComparison:
    """Test tolerance-based comparison."""

    def test_exact_match(self, engine):
        assert engine._compare_within_tolerance(5.0, 5.0, 0.0) is True

    def test_exact_mismatch(self, engine):
        assert engine._compare_within_tolerance(5.0, 5.001, 0.0) is False

    def test_within_tolerance(self, engine):
        assert engine._compare_within_tolerance(5.0, 5.005, 0.01) is True

    def test_outside_tolerance(self, engine):
        assert engine._compare_within_tolerance(5.0, 5.02, 0.01) is False


class TestCalculationExecution:
    """Test full calculation execution with recomputation."""

    def test_pressure_reading_pass(self, engine):
        request = CalculationRequest(
            parameter_name="pressure_reading",
            formula="measured_pressure",
            input_values={"measured_pressure": 4.2},
            threshold=5.0,
            threshold_operator="<=",
            tolerance=0.001,
            evidence_reference="ev-test-001",
            unit="Bar",
        )
        result = engine.execute_calculation(request)

        assert result.status == "PASS"
        assert result.primary_result == 4.2
        assert result.recomputed_result == 4.2
        assert result.results_match is True
        assert result.threshold_met is True

    def test_threshold_exceeded_fail(self, engine):
        request = CalculationRequest(
            parameter_name="temperature",
            formula="measured_temp",
            input_values={"measured_temp": 72.0},
            threshold=65.0,
            threshold_operator="<=",
            tolerance=0.01,
            evidence_reference="ev-test-002",
            unit="°C",
        )
        result = engine.execute_calculation(request)

        assert result.status == "FAIL"
        assert result.threshold_met is False
        assert result.results_match is True  # Recomputation still matches

    def test_recomputation_always_matches(self, engine):
        """Independent recomputation must match for deterministic formulas."""
        request = CalculationRequest(
            parameter_name="complex_calc",
            formula="sqrt(x**2 + y**2) * z",
            input_values={"x": 3.0, "y": 4.0, "z": 2.0},
            threshold=15.0,
            threshold_operator="<=",
            evidence_reference="ev-test-003",
        )
        result = engine.execute_calculation(request)

        assert result.results_match is True
        assert abs(result.primary_result - 10.0) < 1e-10
        assert abs(result.recomputed_result - 10.0) < 1e-10

    def test_provenance_chain_populated(self, engine):
        request = CalculationRequest(
            parameter_name="test_param",
            formula="a + b",
            input_values={"a": 1.0, "b": 2.0},
            threshold=5.0,
            evidence_reference="ev-test-004",
        )
        result = engine.execute_calculation(request)

        assert result.provenance["source"] == "deterministic_compute_engine"
        assert result.provenance["evidence_id"] == "ev-test-004"
        assert result.provenance["formula"] == "a + b"
        assert result.provenance["results_match"] is True

    def test_batch_execution(self, engine):
        requests = [
            CalculationRequest(
                parameter_name=f"param_{i}",
                formula="x",
                input_values={"x": float(i)},
                threshold=10.0,
                evidence_reference=f"ev-batch-{i}",
            )
            for i in range(5)
        ]
        results = engine.execute_batch(requests)
        assert len(results) == 5
        assert all(r.status == "PASS" for r in results)


class TestInspectionCalculationBuilder:
    """Test the flagship inspection calculation builder."""

    def test_extracts_pressure_from_evidence(self, engine):
        from app.schemas.evidence import EvidenceObject, NormalizedRegion
        from shared.enums import EvidenceType

        ev = EvidenceObject(
            document_id="doc-1",
            source_hash="abc123",
            page_number=1,
            region=NormalizedRegion(x=0.0, y=0.0, width=1.0, height=1.0),
            extracted_text="Pressure: 4.2 Bar | Status: PASS",
            evidence_type=EvidenceType.TABLE,
        )

        calcs = engine.build_inspection_calculations([ev])
        assert len(calcs) >= 1
        pressure_calcs = [c for c in calcs if c.parameter_name == "pressure_reading"]
        assert len(pressure_calcs) == 1
        assert pressure_calcs[0].threshold == 5.0
