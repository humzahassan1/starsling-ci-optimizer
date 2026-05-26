"""MCP server — exposes CI optimization tools via the Model Context Protocol."""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.analyzer import analyze_workflow
from src.feedback import FeedbackStore
from src.rules import ALL_RULES


# Initialize the MCP server
mcp = FastMCP(
    "starsling-ci-optimizer",
    version="0.1.0",
    description="Analyzes GitHub Actions workflows and suggests optimizations",
)

# Initialize feedback store
feedback_store = FeedbackStore()


@mcp.tool()
def analyze_workflow_tool(
    yaml_content: str,
    workflow_name: str = "workflow.yml",
    repo: str = "default",
) -> str:
    """Analyze a GitHub Actions workflow YAML and return optimization suggestions.

    Args:
        yaml_content: The raw YAML content of a GitHub Actions workflow file.
        workflow_name: Name of the workflow file (for reporting).
        repo: Repository identifier for feedback tracking.

    Returns:
        A Markdown-formatted optimization report with findings.
    """
    try:
        report = analyze_workflow(yaml_content, workflow_name)

        # Check feedback history and deprioritize rejected rule types
        deprioritized = []
        filtered_findings = []
        for finding in report.findings:
            rule_prefix = finding.id.rsplit("-", 1)[0]
            if feedback_store.should_deprioritize(repo, rule_prefix):
                deprioritized.append(finding.rule)
            else:
                filtered_findings.append(finding)

        report.findings = filtered_findings

        markdown = report.to_markdown()

        if deprioritized:
            unique_rules = list(set(deprioritized))
            markdown += (
                "\n\n---\n"
                f"*Note: {len(unique_rules)} rule type(s) were deprioritized based "
                f"on past feedback: {', '.join(unique_rules)}*"
            )

        # Append JSON summary for programmatic use
        markdown += "\n\n<details>\n<summary>JSON Report</summary>\n\n```json\n"
        markdown += json.dumps(report.to_dict(), indent=2)
        markdown += "\n```\n</details>"

        return markdown

    except ValueError as e:
        return f"**Error:** {str(e)}"
    except Exception as e:
        return f"**Error:** Unexpected failure during analysis: {str(e)}"


@mcp.tool()
def get_optimization_detail(finding_id: str, yaml_content: str) -> str:
    """Get a detailed explanation of a specific optimization finding.

    Args:
        finding_id: The ID of the finding (e.g., 'cache-lint', 'install-test').
        yaml_content: The original workflow YAML (needed to re-run analysis).

    Returns:
        Detailed Markdown explanation of the finding with context.
    """
    try:
        report = analyze_workflow(yaml_content)
        finding = next((f for f in report.findings if f.id == finding_id), None)

        if not finding:
            available = [f.id for f in report.findings]
            return (
                f"**Error:** Finding '{finding_id}' not found.\n\n"
                f"Available finding IDs: {', '.join(available)}"
            )

        detail = f"""# {finding.title}

**Severity:** {finding.severity.value}
**Category:** {finding.category.value}
**Estimated Impact:** {finding.estimated_impact}
**Affected Jobs:** {', '.join(finding.affected_jobs)}

## What's Wrong

{finding.description}

## Before

```yaml
{finding.before_yaml}
```

## After (Recommended)

```yaml
{finding.after_yaml}
```

## Why This Matters

{"This is a **critical** issue. " if finding.severity.value == "critical" else ""}"""

        impact_explanations = {
            "caching": (
                "Dependency caching is the single highest-impact CI optimization. "
                "Without it, every job downloads and installs all packages from "
                "scratch. With caching, subsequent runs skip the download entirely "
                "and restore from cache in seconds."
            ),
            "install": (
                "Using the correct install command for CI ensures deterministic, "
                "reproducible builds. `npm ci` deletes `node_modules` and installs "
                "exactly what's in the lockfile — faster and safer than `npm install`."
            ),
            "concurrency": (
                "Without concurrency controls, pushing 5 commits in quick succession "
                "runs 5 full CI pipelines. With `cancel-in-progress: true`, each new "
                "push cancels the previous run, saving runner minutes."
            ),
            "parallelization": (
                "Sequential jobs that don't depend on each other's output waste time "
                "waiting. Running them in parallel uses more runners but finishes "
                "faster — often cutting total CI time by 50% or more."
            ),
            "redundancy": (
                "Running the same build command in multiple jobs wastes compute. "
                "Build once, upload the artifact, and download it in downstream jobs."
            ),
            "actions": (
                "Newer action versions include performance improvements, security "
                "fixes, and new features. Staying current reduces risk and often "
                "speeds up execution."
            ),
            "sharding": (
                "Test sharding splits your test suite across multiple parallel runners. "
                "If your tests take 10 minutes on one runner, sharding across 3 runners "
                "can bring that down to ~3.5 minutes."
            ),
        }

        detail += impact_explanations.get(finding.category.value, "")
        return detail

    except Exception as e:
        return f"**Error:** {str(e)}"


@mcp.tool()
def list_rules() -> str:
    """List all available optimization rules with descriptions.

    Returns:
        Markdown-formatted list of all rules and their severity levels.
    """
    rules_info = {
        "check_missing_cache": {
            "name": "Missing Dependency Cache",
            "severity": "critical",
            "description": "Detects jobs that install dependencies without caching.",
        },
        "check_install_commands": {
            "name": "Inefficient Install Commands",
            "severity": "warning",
            "description": "Flags npm install (should be npm ci) and missing --frozen-lockfile.",
        },
        "check_missing_concurrency": {
            "name": "Missing Concurrency Controls",
            "severity": "warning",
            "description": "Flags workflows without concurrency groups for push/PR triggers.",
        },
        "check_outdated_actions": {
            "name": "Outdated Action Versions",
            "severity": "info",
            "description": "Catches use of old action versions when newer ones are available.",
        },
        "check_sequential_jobs": {
            "name": "Sequential Parallelizable Jobs",
            "severity": "warning",
            "description": "Identifies independent jobs chained via 'needs' that could run in parallel.",
        },
        "check_redundant_builds": {
            "name": "Redundant Build Steps",
            "severity": "critical",
            "description": "Detects the same build command running in multiple jobs.",
        },
        "check_missing_sharding": {
            "name": "Missing Test Sharding",
            "severity": "info",
            "description": "Suggests matrix strategies for test jobs without sharding.",
        },
    }

    lines = ["# CI Optimization Rules", "", f"**{len(rules_info)} rules available**", ""]

    for func_name, info in rules_info.items():
        severity_badge = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }[info["severity"]]

        lines.append(f"### {severity_badge} {info['name']}")
        lines.append(f"**Severity:** {info['severity']}")
        lines.append(f"{info['description']}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def submit_feedback(
    finding_id: str,
    accepted: bool,
    repo: str = "default",
    reason: str = "",
) -> str:
    """Submit feedback on an optimization suggestion (accept or reject).

    Args:
        finding_id: The ID of the finding being reviewed.
        accepted: True to accept the suggestion, False to reject it.
        repo: Repository identifier for tracking.
        reason: Optional reason for accepting/rejecting.

    Returns:
        Confirmation message with updated statistics.
    """
    try:
        entry = feedback_store.submit(
            repo=repo,
            finding_id=finding_id,
            accepted=accepted,
            reason=reason if reason else None,
        )

        stats = feedback_store.get_stats(repo)
        action = "accepted" if accepted else "rejected"

        return (
            f"**Feedback recorded:** {action} `{finding_id}`\n\n"
            f"**Repository Stats:**\n"
            f"- Total feedback: {stats['total_feedback']}\n"
            f"- Accepted: {stats['accepted']}\n"
            f"- Rejected: {stats['rejected']}"
        )

    except Exception as e:
        return f"**Error:** {str(e)}"


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()