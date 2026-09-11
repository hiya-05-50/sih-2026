from __future__ import annotations

"""Sprint 6 – Evidence Conflict Detector.

Detects conflicting evidence within an evidence set. Conflicts are
defined as multiple evidence objects claiming different values for
the same measured parameter (e.g., two readings of "temperature"
that disagree beyond tolerance).

Conflicts are surfaced explicitly — never silently averaged or hidden.
Per Master PRD: conflicting evidence must be routed to verification/review.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.schemas.evidence import EvidenceObject

logger = logging.getLogger(__name__)

# Patterns that identify a key-value measurement in extracted text
_MEASUREMENT_PATTERN = re.compile(
    r"(?P<param>[A-Za-z][A-Za-z_ ]+?)\s*[:=]\s*(?P<value>[\d.]+)\s*(?P<unit>[A-Za-z°/%]*)",
    re.IGNORECASE,
)


@dataclass
class EvidenceConflict:
    """A detected conflict between evidence objects."""

    parameter: str
    evidence_a_id: str
    evidence_a_value: str
    evidence_b_id: str
    evidence_b_value: str
    severity: str  # "WARNING" or "CRITICAL"
    detail: str


@dataclass
class ConflictReport:
    """Summary of all detected conflicts in an evidence set."""

    total_parameters_checked: int = 0
    conflicts: List[EvidenceConflict] = field(default_factory=list)
    has_conflicts: bool = False

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    @property
    def critical_count(self) -> int:
        return sum(1 for c in self.conflicts if c.severity == "CRITICAL")


def detect_conflicts(
    evidence_objects: List[EvidenceObject],
    tolerance_pct: float = 10.0,
) -> ConflictReport:
    """Detect conflicting values across evidence objects.

    Two evidence objects conflict when they report different numeric
    values for the same parameter name and the difference exceeds
    the tolerance percentage.

    Args:
        evidence_objects: Evidence objects to check.
        tolerance_pct: Percentage tolerance for numeric disagreement.

    Returns:
        ConflictReport with all detected conflicts.
    """
    # Extract parameter → [(evidence_id, value_str, value_float)] mappings
    param_values: Dict[str, List[Tuple[str, str, float]]] = {}

    for ev in evidence_objects:
        text = ev.extracted_text or ""
        for match in _MEASUREMENT_PATTERN.finditer(text):
            param = match.group("param").strip().lower()
            value_str = match.group("value")
            try:
                value_float = float(value_str)
            except ValueError:
                continue
            unit = match.group("unit").strip()
            key = f"{param}" + (f" ({unit})" if unit else "")
            if key not in param_values:
                param_values[key] = []
            param_values[key].append((ev.evidence_id, value_str, value_float))

    report = ConflictReport(total_parameters_checked=len(param_values))
    conflicts: List[EvidenceConflict] = []

    for param, values in param_values.items():
        if len(values) < 2:
            continue

        # Compare all pairs
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                ev_a_id, ev_a_str, ev_a_val = values[i]
                ev_b_id, ev_b_str, ev_b_val = values[j]

                if ev_a_id == ev_b_id:
                    continue

                # Calculate disagreement
                avg = (abs(ev_a_val) + abs(ev_b_val)) / 2.0
                if avg == 0:
                    continue
                diff_pct = abs(ev_a_val - ev_b_val) / avg * 100.0

                if diff_pct > tolerance_pct:
                    severity = "CRITICAL" if diff_pct > 50.0 else "WARNING"
                    conflicts.append(EvidenceConflict(
                        parameter=param,
                        evidence_a_id=ev_a_id,
                        evidence_a_value=ev_a_str,
                        evidence_b_id=ev_b_id,
                        evidence_b_value=ev_b_str,
                        severity=severity,
                        detail=(
                            f"Parameter '{param}': evidence {ev_a_id} reports "
                            f"{ev_a_str} vs evidence {ev_b_id} reports {ev_b_str} "
                            f"(disagreement: {diff_pct:.1f}%, tolerance: {tolerance_pct}%)"
                        ),
                    ))

    report.conflicts = conflicts
    report.has_conflicts = len(conflicts) > 0

    if conflicts:
        logger.warning(
            "Detected %d evidence conflict(s) across %d parameters",
            len(conflicts), len(param_values),
        )

    return report
