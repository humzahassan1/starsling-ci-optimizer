"""Rule: Suggest test sharding and matrix strategies."""

from src.models import Finding, Severity, Category


# Common test commands to look for
TEST_COMMANDS = [
    "npm test",
    "npm run test",
    "yarn test",
    "pnpm test",
    "bun test",
    "pytest",
    "cargo test",
    "go test",
    "jest",
    "vitest",
    "npx jest",
    "npx vitest",
]


def check_missing_sharding(workflow: dict) -> list[Finding]:
    """Check for test jobs that could benefit from sharding or matrix strategies."""
    findings = []
    jobs = workflow.get("jobs", {})

    for job_name, job_config in jobs.items():
        steps = job_config.get("steps", [])
        has_matrix = "matrix" in str(job_config.get("strategy", {}))
        has_test_cmd = False
        test_cmd_found = ""

        for step in steps:
            run_cmd = step.get("run", "").strip()
            for test_cmd in TEST_COMMANDS:
                if test_cmd in run_cmd:
                    has_test_cmd = True
                    test_cmd_found = test_cmd
                    break

        if has_test_cmd and not has_matrix:
            findings.append(Finding(
                id=f"shard-{job_name}",
                rule="missing-test-sharding",
                severity=Severity.INFO,
                category=Category.SHARDING,
                title=f"Consider Test Sharding for '{job_name}'",
                description=(
                    f"The '{job_name}' job runs tests without a matrix strategy. "
                    f"For large test suites, splitting tests across parallel runners "
                    f"can dramatically reduce wall-clock time."
                ),
                affected_jobs=[job_name],
                before_yaml=(
                    f"{job_name}:\n"
                    f"  steps:\n"
                    f"    - run: {test_cmd_found}"
                ),
                after_yaml=(
                    f"{job_name}:\n"
                    f"  strategy:\n"
                    f"    matrix:\n"
                    f"      shard: [1, 2, 3]\n"
                    f"  steps:\n"
                    f"    - run: {test_cmd_found} --shard=${{{{ matrix.shard }}}}/3"
                ),
                estimated_impact="medium",
            ))

    return findings