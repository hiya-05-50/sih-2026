"""Sprint 5 – SIAB Benchmark Harness Tests.

Tests:
  - Three-config benchmark structure (Config 1, 2, 3)
  - Comparison table generation
  - Report storage and retrieval
  - 'TO BE VALIDATED' honesty (no fabricated numbers)
"""

import asyncio
import pytest

from app.services.siab import SIABRunner, SIABReport
from app.services.audit import AuditEventStore


@pytest.fixture
def audit_store():
    return AuditEventStore()


@pytest.fixture
def runner(audit_store):
    return SIABRunner(audit_store=audit_store)


class TestSIABThreeConfigStructure:
    """Test the mandatory three-configuration benchmark structure."""

    def test_benchmark_returns_report(self, runner):
        """Benchmark must return a SIABReport."""
        report = asyncio.run(runner.run_benchmark())
        assert isinstance(report, SIABReport)

    def test_three_configs(self, runner):
        """Report must contain exactly 3 configurations."""
        report = asyncio.run(runner.run_benchmark())
        assert len(report.configs) == 3

    def test_config_ids(self, runner):
        """Config IDs must be config-1, config-2, config-3."""
        report = asyncio.run(runner.run_benchmark())
        config_ids = [c.config_id for c in report.configs]
        assert "config-1" in config_ids
        assert "config-2" in config_ids
        assert "config-3" in config_ids

    def test_config1_is_baseline(self, runner):
        """Config 1 must be the single-model baseline (no scaffolding)."""
        report = asyncio.run(runner.run_benchmark())
        c1 = [c for c in report.configs if c.config_id == "config-1"][0]
        assert "baseline" in c1.config_name.lower() or "single model" in c1.config_name.lower()

    def test_config2_is_agent_plus_tools(self, runner):
        """Config 2 must be agent + tools (no verification)."""
        report = asyncio.run(runner.run_benchmark())
        c2 = [c for c in report.configs if c.config_id == "config-2"][0]
        assert "agent" in c2.config_name.lower() or "tool" in c2.config_name.lower()

    def test_config3_is_full_safire(self, runner):
        """Config 3 must be full SAFIRE pipeline."""
        report = asyncio.run(runner.run_benchmark())
        c3 = [c for c in report.configs if c.config_id == "config-3"][0]
        assert "safire" in c3.config_name.lower() or "full" in c3.config_name.lower()


class TestSIABHonesty:
    """Test that SIAB never fabricates benchmark numbers."""

    def test_no_fabricated_percentages(self, runner):
        """Model-dependent metrics must be 'TO BE VALIDATED', not invented."""
        report = asyncio.run(runner.run_benchmark())
        for config in report.configs:
            # These are model-dependent and cannot be measured without Ollama
            for key in ["extraction_correctness", "answer_correctness"]:
                if key in config.metrics:
                    val = config.metrics[key]
                    # Must be "TO BE VALIDATED", not a fake number
                    assert val == "TO BE VALIDATED" or val.startswith("N/A"), (
                        f"Config {config.config_id}, metric {key} = {val} — "
                        f"must be 'TO BE VALIDATED' without model availability"
                    )

    def test_comparison_table_exists(self, runner):
        """Report must include a comparison table."""
        report = asyncio.run(runner.run_benchmark())
        assert len(report.comparison_table) > 0

    def test_comparison_table_has_key_metrics(self, runner):
        """Comparison table must include key PRD metrics."""
        report = asyncio.run(runner.run_benchmark())
        metric_names = [m.name for m in report.comparison_table]
        # Must include at least these per PRD §29
        assert any("extraction" in m.lower() for m in metric_names)
        assert any("latency" in m.lower() for m in metric_names)
        assert any("security" in m.lower() for m in metric_names)


class TestSIABReportStorage:
    """Test report storage and retrieval."""

    def test_no_reports_initially(self, runner):
        """No reports before running the benchmark."""
        assert len(runner.get_reports()) == 0
        assert runner.get_latest_report() is None

    def test_report_stored_after_run(self, runner):
        """Report must be stored after running the benchmark."""
        asyncio.run(runner.run_benchmark())
        assert len(runner.get_reports()) == 1

    def test_latest_report(self, runner):
        """get_latest_report() returns the most recent."""
        asyncio.run(runner.run_benchmark())
        asyncio.run(runner.run_benchmark())
        assert len(runner.get_reports()) == 2
        latest = runner.get_latest_report()
        assert latest is not None

    def test_audit_event_recorded(self, runner, audit_store):
        """Benchmark run must create an audit event."""
        from app.schemas.audit import AuditEventType
        asyncio.run(runner.run_benchmark())
        events = audit_store.list_events(
            event_type=AuditEventType.VERIFICATION_RUN
        )
        assert len(events) >= 1

    def test_report_has_execution_time(self, runner):
        """Report must record total execution time."""
        report = asyncio.run(runner.run_benchmark())
        # On fast machines, execution can complete in <1ms (time.time() precision)
        assert report.total_execution_time_ms >= 0

    def test_report_has_timestamp(self, runner):
        """Report must have a timestamp."""
        report = asyncio.run(runner.run_benchmark())
        assert report.timestamp is not None
        assert len(report.timestamp) > 0

    def test_report_has_unique_id(self, runner):
        """Report must have a unique ID."""
        report = asyncio.run(runner.run_benchmark())
        assert report.report_id.startswith("siab-")
