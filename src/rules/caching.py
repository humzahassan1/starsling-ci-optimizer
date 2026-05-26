"""Rule: Detect missing dependency caching in CI workflows."""

from src.models import Finding, Severity, Category


# Package managers and their cache keys for setup actions
PACKAGE_MANAGERS = {
    "npm": {
        "install_patterns": ["npm install", "npm ci"],
        "cache_key": "npm",
        "setup_action": "actions/setup-node",
    },
    "yarn": {
        "install_patterns": ["yarn install", "yarn"],
        "cache_key": "yarn",
        "setup_action": "actions/setup-node",
    },
    "pnpm": {
        "install_patterns": ["pnpm install", "pnpm i"],
        "cache_key": "pnpm",
        "setup_action": "actions/setup-node",
    },
    "bun": {
        "install_patterns": ["bun install", "bun i"],
        "cache_key": "bun",
        "setup_action": "oven-sh/setup-bun",
    },
    "pip": {
        "install_patterns": ["pip install"],
        "cache_key": "pip",
        "setup_action": "actions/setup-python",
    },
    "cargo": {
        "install_patterns": ["cargo build", "cargo test"],
        "cache_key": "cargo",
        "setup_action": None,
    },
}


def check_missing_cache(workflow: dict) -> list[Finding]:
    """Check for jobs that install dependencies without caching."""
    findings = []
    jobs = workflow.get("jobs", {})

    for job_name, job_config in jobs.items():
        steps = job_config.get("steps", [])
        has_cache = False
        detected_managers = []

        for step in steps:
            # Check if actions/cache is used
            uses = step.get("uses", "")
            if "actions/cache" in uses:
                has_cache = True

            # Check if setup action has cache option enabled
            with_config = step.get("with", {})
            if isinstance(with_config, dict) and with_config.get("cache"):
                has_cache = True

            # Detect package manager install commands
            run_cmd = step.get("run", "")
            for manager, config in PACKAGE_MANAGERS.items():
                for pattern in config["install_patterns"]:
                    if pattern in run_cmd and manager not in detected_managers:
                        detected_managers.append(manager)

        # If we found installs but no caching, flag it
        if detected_managers and not has_cache:
            manager = detected_managers[0]
            config = PACKAGE_MANAGERS[manager]

            before = f"- run: {config['install_patterns'][0]}"

            if config["setup_action"]:
                after = (
                    f"- uses: {config['setup_action']}@v4\n"
                    f"    with:\n"
                    f"      cache: '{config['cache_key']}'\n"
                    f"  - run: {config['install_patterns'][-1]}"
                )
            else:
                after = (
                    f"- uses: actions/cache@v4\n"
                    f"    with:\n"
                    f"      path: ~/.{manager}\n"
                    f"      key: ${{{{ runner.os }}}}-{manager}-${{{{ hashFiles('**/lock*') }}}}"
                )

            findings.append(Finding(
                id=f"cache-{job_name}",
                rule="missing-dependency-cache",
                severity=Severity.CRITICAL,
                category=Category.CACHING,
                title=f"Missing Dependency Caching in '{job_name}'",
                description=(
                    f"The '{job_name}' job installs {manager} dependencies without "
                    f"caching. Every run downloads and installs packages from scratch, "
                    f"adding 30-90 seconds per job."
                ),
                affected_jobs=[job_name],
                before_yaml=before,
                after_yaml=after,
                estimated_impact="high",
            ))

    return findings