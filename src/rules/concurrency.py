"""Rule: Detect missing concurrency controls in CI workflows."""

from src.models import Finding, Severity, Category


def check_missing_concurrency(workflow: dict) -> list[Finding]:
    """Check if the workflow is missing concurrency group configuration."""
    findings = []

    if "concurrency" not in workflow:
        # Determine which events trigger this workflow
        triggers = workflow.get("on", workflow.get(True, {}))
        trigger_names = []

        if isinstance(triggers, dict):
            trigger_names = list(triggers.keys())
        elif isinstance(triggers, list):
            trigger_names = triggers
        elif isinstance(triggers, str):
            trigger_names = [triggers]

        # Concurrency controls matter most for push/PR triggers
        relevant_triggers = [t for t in trigger_names if t in ("push", "pull_request", "pull_request_target")]

        if relevant_triggers:
            all_jobs = list(workflow.get("jobs", {}).keys())

            findings.append(Finding(
                id="concurrency-global",
                rule="missing-concurrency",
                severity=Severity.WARNING,
                category=Category.CONCURRENCY,
                title="Missing Concurrency Controls",
                description=(
                    "This workflow has no concurrency group. Rapid pushes will "
                    "queue up redundant runs instead of canceling in-progress ones. "
                    "This wastes runner minutes and slows down feedback."
                ),
                affected_jobs=all_jobs,
                before_yaml="# No concurrency configuration",
                after_yaml=(
                    "concurrency:\n"
                    "  group: ${{ github.workflow }}-${{ github.ref }}\n"
                    "  cancel-in-progress: true"
                ),
                estimated_impact="medium",
            ))

    return findings