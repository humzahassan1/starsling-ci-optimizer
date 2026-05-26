"""Rule: Detect redundant build steps across jobs."""

from src.models import Finding, Severity, Category


# Common build commands to look for
BUILD_COMMANDS = [
    "npm run build",
    "yarn build",
    "pnpm build",
    "bun run build",
    "cargo build",
    "go build",
    "make build",
    "python setup.py build",
]


def check_redundant_builds(workflow: dict) -> list[Finding]:
    """Check for the same build command running in multiple jobs."""
    findings = []
    jobs = workflow.get("jobs", {})

    # Track which jobs run which build commands
    build_jobs: dict[str, list[str]] = {}

    for job_name, job_config in jobs.items():
        steps = job_config.get("steps", [])

        for step in steps:
            run_cmd = step.get("run", "").strip()

            for build_cmd in BUILD_COMMANDS:
                if build_cmd in run_cmd:
                    build_jobs.setdefault(build_cmd, []).append(job_name)

    # Flag build commands that appear in multiple jobs
    for build_cmd, job_names in build_jobs.items():
        if len(job_names) >= 2:
            findings.append(Finding(
                id=f"redundant-build-{job_names[0]}",
                rule="redundant-build-step",
                severity=Severity.CRITICAL,
                category=Category.REDUNDANCY,
                title="Redundant Build Steps",
                description=(
                    f"'{build_cmd}' runs in multiple jobs: [{', '.join(job_names)}]. "
                    f"Build once in an upstream job and pass the artifact downstream "
                    f"using actions/upload-artifact and actions/download-artifact."
                ),
                affected_jobs=job_names,
                before_yaml=(
                    f"# '{build_cmd}' duplicated in:\n"
                    + "\n".join(f"# - {j}" for j in job_names)
                ),
                after_yaml=(
                    f"build:\n"
                    f"  steps:\n"
                    f"    - run: {build_cmd}\n"
                    f"    - uses: actions/upload-artifact@v4\n"
                    f"      with:\n"
                    f"        name: build-output\n"
                    f"        path: dist/\n\n"
                    f"deploy:\n"
                    f"  needs: build\n"
                    f"  steps:\n"
                    f"    - uses: actions/download-artifact@v4"
                ),
                estimated_impact="high",
            ))

    return findings