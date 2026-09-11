"""Sprint 5 – SIAB Harness Tests.

Covers:
  - All three SIAB configurations are supported
  - Fixed benchmark prompt is consistent across configs
  - Unmeasured metrics default to "TO BE VALIDATED"
  - Config 1 (bare model) runs and records latency
  - Config 2 (agent + tools) runs and records latency
  - Config 3 (full SAFIRE) runs via the flagship pipeline
  - run_all() produces a comparative report
  - Error handling for missing adapters/pipelines
  - History tracking
  - No fake measurements are invented
"""

from __future__ import annotations

import asyncio

import pytest

from app.services.sovereignty.siab_harness import (
    SIAB_BENCHMARK_PROMPT,
    TO_BE_VALIDATED,
    SIABHarness,
    SIABMetrics,
    SIABReport,
    SIABRunResult,
)
from shared.enums import SIABConfig


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _make_harness_no_deps() -> SIABHarness:
    """Harness with no adapter/pipeline — validates structure only."""
    return SIABHarness(adapter_manager=None, flagship_pipeline=None)


def _make_harness_with_adapters() -> SIABHarness:
    """Harness with real fixture adapters from the test seed."""
    from app.adapters.manager import AdapterManager
    from app.services.registry import ModelRegistry
    from app.services.seed import seed_models

    registry = ModelRegistry()
    asyncio.run(seed_models(registry))
    adapter_manager = AdapterManager(registry)
    return SIABHarness(adapter_manager=adapter_manager)


def _make_full_harness() -> SIABHarness:
    """Harness wired with adapters AND the flagship pipeline."""
    from app.adapters.manager import AdapterManager
    from app.services.approval import ApprovalService
    from app.services.flagship_pipeline import FlagshipPipeline
    from app.services.registry import ModelRegistry
    from app.services.seed import seed_models

    registry = ModelRegistry()
    asyncio.run(seed_models(registry))
    adapter_manager = AdapterManager(registry)
    approval = ApprovalService()
    pipeline = FlagshipPipeline(adapter_manager, approval)
    return SIABHarness(
        adapter_manager=adapter_manager,
        flagship_pipeline=pipeline,
    )


# -----------------------------------------------------------------------
# Configuration tests
# -----------------------------------------------------------------------


class TestSIABConfigurations:
    """Verify SIAB configuration definitions."""

    def test_exactly_three_configs_supported(self):
        harness = _make_harness_no_deps()
        configs = harness.get_supported_configs()
        assert len(configs) == 3

    def test_config_names_match_enum(self):
        harness = _make_harness_no_deps()
        configs = harness.get_supported_configs()
        assert SIABConfig.BARE_MODEL in configs
        assert SIABConfig.AGENT_NO_FABRIC in configs
        assert SIABConfig.FULL_SAFIRE in configs

    def test_fixed_benchmark_prompt_is_consistent(self):
        """All configs use the same fixed prompt."""
        assert len(SIAB_BENCHMARK_PROMPT) > 0
        result1 = SIABRunResult(config=SIABConfig.BARE_MODEL)
        result2 = SIABRunResult(config=SIABConfig.AGENT_NO_FABRIC)
        result3 = SIABRunResult(config=SIABConfig.FULL_SAFIRE)
        assert result1.prompt == result2.prompt == result3.prompt


# -----------------------------------------------------------------------
# TO BE VALIDATED sentinel
# -----------------------------------------------------------------------


class TestToBeValidated:
    """Metrics that have not been measured must use the sentinel."""

    def test_default_metrics_are_to_be_validated(self):
        metrics = SIABMetrics()
        assert metrics.latency_ms == TO_BE_VALIDATED
        assert metrics.accuracy == TO_BE_VALIDATED
        assert metrics.evidence_count == TO_BE_VALIDATED
        assert metrics.verification_passed == TO_BE_VALIDATED
        assert metrics.artifacts_generated == TO_BE_VALIDATED

    def test_sentinel_value_is_string(self):
        assert TO_BE_VALIDATED == "TO BE VALIDATED"

    def test_run_result_with_no_deps_has_unvalidated_metrics(self):
        harness = _make_harness_no_deps()
        result = _run(harness.run_config(SIABConfig.BARE_MODEL))
        assert result.metrics.latency_ms == TO_BE_VALIDATED
        assert result.metrics.accuracy == TO_BE_VALIDATED
        assert result.error is None


# -----------------------------------------------------------------------
# Config 1: Bare model
# -----------------------------------------------------------------------


class TestConfig1BareModel:
    """Config 1 — single model, no scaffolding."""

    def test_bare_model_runs_with_fixture_adapter(self):
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.BARE_MODEL))
        assert result.config == SIABConfig.BARE_MODEL
        assert result.error is None

    def test_bare_model_measures_latency(self):
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.BARE_MODEL))
        assert isinstance(result.metrics.latency_ms, float)
        assert result.metrics.latency_ms > 0

    def test_bare_model_records_response(self):
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.BARE_MODEL))
        assert result.metrics.response_text is not None
        assert len(result.metrics.response_text) > 0

    def test_bare_model_accuracy_not_invented(self):
        """Accuracy requires human evaluation — must be TO BE VALIDATED."""
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.BARE_MODEL))
        assert result.metrics.accuracy == TO_BE_VALIDATED

    def test_bare_model_has_no_evidence_or_artifacts(self):
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.BARE_MODEL))
        assert result.metrics.evidence_count == 0
        assert result.metrics.artifacts_generated == 0


# -----------------------------------------------------------------------
# Config 2: Agent + tools, no fabric
# -----------------------------------------------------------------------


class TestConfig2AgentNoFabric:
    """Config 2 — agent with tools but no verification fabric."""

    def test_agent_runs_with_fixture_adapter(self):
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.AGENT_NO_FABRIC))
        assert result.config == SIABConfig.AGENT_NO_FABRIC
        assert result.error is None

    def test_agent_measures_latency(self):
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.AGENT_NO_FABRIC))
        assert isinstance(result.metrics.latency_ms, float)
        assert result.metrics.latency_ms > 0

    def test_agent_accuracy_not_invented(self):
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.AGENT_NO_FABRIC))
        assert result.metrics.accuracy == TO_BE_VALIDATED

    def test_agent_has_no_verification(self):
        harness = _make_harness_with_adapters()
        result = _run(harness.run_config(SIABConfig.AGENT_NO_FABRIC))
        assert result.metrics.verification_passed == "N/A"


# -----------------------------------------------------------------------
# Config 3: Full SAFIRE
# -----------------------------------------------------------------------


class TestConfig3FullSAFIRE:
    """Config 3 — complete SAFIRE pipeline."""

    def test_full_safire_runs(self):
        harness = _make_full_harness()
        result = _run(harness.run_config(SIABConfig.FULL_SAFIRE))
        assert result.config == SIABConfig.FULL_SAFIRE
        assert result.error is None

    def test_full_safire_measures_latency(self):
        harness = _make_full_harness()
        result = _run(harness.run_config(SIABConfig.FULL_SAFIRE))
        assert isinstance(result.metrics.latency_ms, float)
        assert result.metrics.latency_ms > 0

    def test_full_safire_produces_evidence(self):
        harness = _make_full_harness()
        result = _run(harness.run_config(SIABConfig.FULL_SAFIRE))
        assert isinstance(result.metrics.evidence_count, int)
        assert result.metrics.evidence_count > 0

    def test_full_safire_produces_artifacts(self):
        harness = _make_full_harness()
        result = _run(harness.run_config(SIABConfig.FULL_SAFIRE))
        assert isinstance(result.metrics.artifacts_generated, int)
        assert result.metrics.artifacts_generated == 3  # DOCX, XLSX, PDF

    def test_full_safire_accuracy_not_invented(self):
        harness = _make_full_harness()
        result = _run(harness.run_config(SIABConfig.FULL_SAFIRE))
        assert result.metrics.accuracy == TO_BE_VALIDATED


# -----------------------------------------------------------------------
# run_all and reporting
# -----------------------------------------------------------------------


class TestRunAllAndReport:
    """Verify comparative report generation."""

    def test_run_all_produces_three_results(self):
        harness = _make_full_harness()
        report = _run(harness.run_all())
        assert isinstance(report, SIABReport)
        assert len(report.runs) == 3
        assert "BARE_MODEL" in report.runs
        assert "AGENT_NO_FABRIC" in report.runs
        assert "FULL_SAFIRE" in report.runs

    def test_run_all_uses_consistent_prompt(self):
        harness = _make_full_harness()
        report = _run(harness.run_all())
        assert report.benchmark_prompt == SIAB_BENCHMARK_PROMPT
        for run in report.runs.values():
            assert run.prompt == SIAB_BENCHMARK_PROMPT

    def test_report_has_timestamp(self):
        harness = _make_full_harness()
        report = _run(harness.run_all())
        assert report.generated_at is not None
        assert "T" in report.generated_at

    def test_history_tracking(self):
        harness = _make_harness_no_deps()
        assert len(harness.get_history()) == 0
        _run(harness.run_all())
        assert len(harness.get_history()) == 1
        _run(harness.run_all())
        assert len(harness.get_history()) == 2


# -----------------------------------------------------------------------
# Error handling
# -----------------------------------------------------------------------


class TestErrorHandling:
    """Errors must be captured, not crash the harness."""

    def test_no_adapter_does_not_crash(self):
        harness = _make_harness_no_deps()
        result = _run(harness.run_config(SIABConfig.BARE_MODEL))
        assert result.error is None  # graceful fallback, not a crash
        assert result.metrics.latency_ms == TO_BE_VALIDATED

    def test_no_pipeline_does_not_crash(self):
        harness = _make_harness_no_deps()
        result = _run(harness.run_config(SIABConfig.FULL_SAFIRE))
        assert result.error is None
        assert result.metrics.latency_ms == TO_BE_VALIDATED

    def test_run_all_no_deps_does_not_crash(self):
        harness = _make_harness_no_deps()
        report = _run(harness.run_all())
        assert len(report.runs) == 3
        for run in report.runs.values():
            assert run.error is None
