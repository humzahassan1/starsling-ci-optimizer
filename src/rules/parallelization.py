"""Rule: Detect sequential jobs that could run in parallel."""

from src.models import Finding, Severity, Category


# Common job names that are typically independent of each other
PARALLELIZABLE_GROUPS = [
    {"lint", "test", "typecheck", "type-check", "format", "check"},
    {"unit-test", "integration-test", "e2e-test", "e2e"},
]


def check_sequential_jobs(workflow: dict) -> list[Finding]:
    """Check for jobs that run sequentially but could be parallelized."""
    findings = []
    jobs = workflow.get("jobs", {})

    if len(jobs) < 2:
        return findings

    # Find jobs that depend on each other via 'needs'
    dependency_chains = []
    for job_name, job_config in jobs.items():
        needs = job_config.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        if needs:
            dependency_chains.append((job_name, needs))

    # Find jobs with no 'needs' that share similar setup patterns
    independent_jobs = [
        name for name, config in jobs.items()
        if not config.get("needs")
    ]

    # Check if any known parallelizable groups exist as sequential chains
    for group in PARALLELIZABLE_GROUPS:
        matching_jobs = [j for j in jobs.keys() if j.lower() in group]

        if len(matching_jobs) < 2:
            continue

        # Check if these jobs form a chain via 'needs'
        chained = []
        for job_name in matching_jobs:
            needs = jobs[job_name].get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            if any(n in matching_jobs for n in needs):
                chained.append(job_name)

        if chained:
            findings.append(Finding(
                id="parallel-group",
                rule="sequential-parallelizable-jobs",
                severity=Severity.WARNING,
                category=Category.PARALLELIZATION,
                title="Sequential Jobs Could Run in Parallel",
                description=(
                    f"Jobs [{', '.join(matching_jobs)}] appear to be independent "
                    f"tasks chained sequentially via 'needs'. Running them in "
                    f"parallel could cut total CI time significantly."
                ),
                affected_jobs=matching_jobs,
                before_yaml=(
                    f"{chained[0]}:\n"
                    f"  needs: [{matching_jobs[0]}]\n"
                    f"  # Waits for previous job to finish"
                ),
                after_yaml=(
                    f"{chained[0]}:\n"
                    f"  # No 'needs' — runs in parallel\n"
                    f"  # Use a shared setup via actions/cache instead"
                ),
                estimated_impact="high",
            ))
            break

    # Detect jobs with duplicate setup steps that could share a cache
    _check_duplicate_setup(jobs, independent_jobs, findings)

    return findings


def _check_duplicate_setup(
    jobs: dict, independent_jobs: list[str], findings: list[Finding]
) -> None:
    """Check for independent jobs with redundant setup steps."""
    if len(independent_jobs) < 2:
        return

    setup_patterns = {}
    for job_name in independent_jobs:
        steps = jobs[job_name].get("steps", [])
        setup_actions = tuple(
            step.get("uses", "").split("@")[0]
            for step in steps
            if step.get("uses", "").startswith("actions/")
        )
        if setup_actions:
            setup_patterns.setdefault(setup_actions, []).append(job_name)

    for pattern, job_names in setup_patterns.items():
        if len(job_names) >= 2:
            findings.append(Finding(
                id="parallel-redundant-setup",
                rule="redundant-parallel-setup",
                severity=Severity.INFO,
                category=Category.PARALLELIZATION,
                title="Parallel Jobs with Redundant Setup",
                description=(
                    f"Jobs [{', '.join(job_names)}] run the same setup actions "
                    f"({', '.join(pattern)}). Consider extracting a reusable "
                    f"composite action or using dependency caching to avoid "
                    f"repeated installs."
                ),
                affected_jobs=job_names,
                before_yaml="# Each job repeats: checkout → setup-node → install",
                after_yaml="# Extract shared setup into a composite action or cache artifacts",
                estimated_impact="medium",
            ))
            break