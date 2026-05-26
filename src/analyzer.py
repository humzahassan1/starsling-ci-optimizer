"""Core analysis engine — runs all rules against a parsed workflow."""

import yaml
from datetime import datetime, timezone

from src.models import AnalysisReport, Finding
from src.rules import ALL_RULES


def parse_workflow(yaml_content: str) -> dict:
    """Parse a YAML workflow string into a dictionary."""
    try:
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")


def analyze_workflow(
    yaml_content: str,
    workflow_name: str = "workflow.yml",
) -> AnalysisReport:
    """Run all rules against a workflow and produce an analysis report.

    Args:
        yaml_content: Raw YAML string of the GitHub Actions workflow.
        workflow_name: Name of the workflow file for the report.

    Returns:
        AnalysisReport with all findings from the rule engine.
    """
    workflow = parse_workflow(yaml_content)

    if not isinstance(workflow, dict):
        raise ValueError("Workflow YAML must be a mapping, not a scalar or list")

    if "jobs" not in workflow:
        raise ValueError("Workflow YAML has no 'jobs' key — is this a GitHub Actions workflow?")

    # Run every rule and collect findings
    all_findings: list[Finding] = []
    for rule_fn in ALL_RULES:
        try:
            findings = rule_fn(workflow)
            all_findings.extend(findings)
        except Exception as e:
            # A single broken rule shouldn't crash the whole analysis
            print(f"Warning: Rule '{rule_fn.__name__}' failed: {e}")

    # Sort by severity: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_findings.sort(key=lambda f: severity_order.get(f.severity.value, 99))

    return AnalysisReport(
        workflow_name=workflow_name,
        analyzed_at=datetime.now(timezone.utc),
        findings=all_findings,
    )