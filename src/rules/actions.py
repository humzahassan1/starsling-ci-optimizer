"""Rule: Detect outdated GitHub Action versions."""

from src.models import Finding, Severity, Category


# Known latest major versions for common actions
LATEST_VERSIONS = {
    "actions/checkout": "v4",
    "actions/setup-node": "v4",
    "actions/setup-python": "v5",
    "actions/setup-java": "v4",
    "actions/setup-go": "v5",
    "actions/cache": "v4",
    "actions/upload-artifact": "v4",
    "actions/download-artifact": "v4",
}


def check_outdated_actions(workflow: dict) -> list[Finding]:
    """Check for outdated action versions in workflow steps."""
    findings = []
    jobs = workflow.get("jobs", {})

    for job_name, job_config in jobs.items():
        steps = job_config.get("steps", [])

        for step in steps:
            uses = step.get("uses", "")
            if not uses or "@" not in uses:
                continue

            action, version = uses.rsplit("@", 1)

            if action in LATEST_VERSIONS:
                latest = LATEST_VERSIONS[action]

                # Compare major versions (v3 < v4, etc.)
                try:
                    current_major = int(version.lstrip("v").split(".")[0])
                    latest_major = int(latest.lstrip("v").split(".")[0])
                except ValueError:
                    continue

                if current_major < latest_major:
                    findings.append(Finding(
                        id=f"action-{job_name}-{action.split('/')[-1]}",
                        rule="outdated-action",
                        severity=Severity.INFO,
                        category=Category.ACTIONS,
                        title=f"Outdated '{action}' in '{job_name}'",
                        description=(
                            f"Using {action}@{version} but {latest} is available. "
                            f"Newer versions include performance improvements and "
                            f"bug fixes."
                        ),
                        affected_jobs=[job_name],
                        before_yaml=f"- uses: {action}@{version}",
                        after_yaml=f"- uses: {action}@{latest}",
                        estimated_impact="low",
                    ))

    return findings