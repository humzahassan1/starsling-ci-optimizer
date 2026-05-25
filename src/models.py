"""Data models for the CI Optimizer."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity levels for optimization findings."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Category(Enum):
    """Categories of CI optimizations."""
    CACHING = "caching"
    PARALLELIZATION = "parallelization"
    INSTALL = "install"
    CONCURRENCY = "concurrency"
    ACTIONS = "actions"
    REDUNDANCY = "redundancy"
    SHARDING = "sharding"


@dataclass
class Finding:
    """A single optimization finding from the analysis engine."""
    id: str
    rule: str
    severity: Severity
    category: Category
    title: str
    description: str
    affected_jobs: list[str]
    before_yaml: str
    after_yaml: str
    estimated_impact: str  # "high", "medium", "low"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule": self.rule,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "affected_jobs": self.affected_jobs,
            "before_yaml": self.before_yaml,
            "after_yaml": self.after_yaml,
            "estimated_impact": self.estimated_impact,
        }


@dataclass
class AnalysisReport:
    """Complete analysis report for a workflow."""
    workflow_name: str
    analyzed_at: datetime
    findings: list[Finding]
    llm_analysis: Optional[dict] = None

    @property
    def summary(self) -> dict:
        return {
            "total_findings": len(self.findings),
            "critical": sum(1 for f in self.findings if f.severity == Severity.CRITICAL),
            "warnings": sum(1 for f in self.findings if f.severity == Severity.WARNING),
            "suggestions": sum(1 for f in self.findings if f.severity == Severity.INFO),
        }

    def to_dict(self) -> dict:
        result = {
            "workflow": self.workflow_name,
            "analyzed_at": self.analyzed_at.isoformat(),
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
        }
        if self.llm_analysis:
            result["llm_analysis"] = self.llm_analysis
        return result

    def to_markdown(self) -> str:
        lines = [
            "# CI Optimization Report",
            "",
            f"**Workflow:** {self.workflow_name}",
            f"**Analysis Date:** {self.analyzed_at.strftime('%Y-%m-%d')}",
            f"**Findings:** {len(self.findings)} optimizations identified",
            "",
        ]

        # Group findings by severity
        for severity in Severity:
            group = [f for f in self.findings if f.severity == severity]
            if not group:
                continue

            header = {
                Severity.CRITICAL: "## Critical",
                Severity.WARNING: "## Warnings",
                Severity.INFO: "## Suggestions",
            }[severity]
            lines.append(header)
            lines.append("")

            for finding in group:
                lines.append(f"### {finding.title}")
                lines.append(f"**Impact:** {finding.estimated_impact}")
                lines.append(f"**Affected Jobs:** {', '.join(finding.affected_jobs)}")
                lines.append("")
                lines.append(f"{finding.description}")
                lines.append("")
                lines.append("**Before:**")
                lines.append("```yaml")
                lines.append(finding.before_yaml)
                lines.append("```")
                lines.append("")
                lines.append("**After:**")
                lines.append("```yaml")
                lines.append(finding.after_yaml)
                lines.append("```")
                lines.append("")

        return "\n".join(lines)


@dataclass
class FeedbackEntry:
    """A single feedback entry for a suggestion."""
    finding_id: str
    accepted: bool
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "accepted": self.accepted,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }