"""Rule registry — collects all rule checks into a single list."""

from src.rules.caching import check_missing_cache
from src.rules.install import check_install_commands
from src.rules.concurrency import check_missing_concurrency
from src.rules.actions import check_outdated_actions
from src.rules.parallelization import check_sequential_jobs
from src.rules.redundancy import check_redundant_builds
from src.rules.sharding import check_missing_sharding

# All rule functions. Each takes a parsed workflow dict and returns list[Finding].
ALL_RULES = [
    check_missing_cache,
    check_install_commands,
    check_missing_concurrency,
    check_outdated_actions,
    check_sequential_jobs,
    check_redundant_builds,
    check_missing_sharding,
]