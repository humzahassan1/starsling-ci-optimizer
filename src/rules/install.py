"""Rule: Detect inefficient install commands in CI workflows."""

from src.models import Finding, Severity, Category


# Maps bad install commands to their CI-optimized equivalents
INSTALL_FIXES = {
    "npm install": {
        "replacement": "npm ci",
        "reason": "npm ci installs from lockfile, is faster, and ensures deterministic builds",
    },
    "yarn install": {
        "replacement": "yarn install --frozen-lockfile",
        "reason": "--frozen-lockfile prevents accidental lockfile updates in CI",
    },
    "pnpm install": {
        "replacement": "pnpm install --frozen-lockfile",
        "reason": "--frozen-lockfile ensures reproducible installs in CI",
    },
}


def check_install_commands(workflow: dict) -> list[Finding]:
    """Check for install commands that should use CI-optimized alternatives."""
    findings = []
    jobs = workflow.get("jobs", {})

    for job_name, job_config in jobs.items():
        steps = job_config.get("steps", [])

        for step in steps:
            run_cmd = step.get("run", "").strip()

            for bad_cmd, fix in INSTALL_FIXES.items():
                # Match exact command, not substring of a longer command
                # e.g. "npm install" but not "npm install --production"
                if run_cmd == bad_cmd or run_cmd.startswith(bad_cmd + "\n"):
                    findings.append(Finding(
                        id=f"install-{job_name}",
                        rule="inefficient-install",
                        severity=Severity.WARNING,
                        category=Category.INSTALL,
                        title=f"Use '{fix['replacement']}' in '{job_name}'",
                        description=fix["reason"],
                        affected_jobs=[job_name],
                        before_yaml=f"- run: {bad_cmd}",
                        after_yaml=f"- run: {fix['replacement']}",
                        estimated_impact="medium",
                    ))

    return findings