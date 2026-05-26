"""CLI entry point for standalone use."""

import sys
from pathlib import Path

import click

from src.analyzer import analyze_workflow
from src.feedback import FeedbackStore


@click.group()
def main():
    """StarSling CI Optimizer — analyze GitHub Actions workflows for optimizations."""
    pass


@main.command()
@click.argument("workflow_path", type=click.Path(exists=True))
@click.option("--name", default=None, help="Workflow name for the report.")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON instead of Markdown.")
@click.option("--no-llm", is_flag=True, help="Skip LLM analysis (rule engine only).")
def analyze(workflow_path: str, name: str, output_json: bool, no_llm: bool):
    """Analyze a GitHub Actions workflow file.

    Example: ci-optimizer analyze .github/workflows/ci.yml
    """
    path = Path(workflow_path)
    workflow_name = name or path.name

    try:
        yaml_content = path.read_text()
    except Exception as e:
        click.echo(f"Error reading file: {e}", err=True)
        sys.exit(1)

    try:
        report = analyze_workflow(
            yaml_content=yaml_content,
            workflow_name=workflow_name,
            use_llm=not no_llm,
        )
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if output_json:
        import json
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(report.to_markdown())


@main.command()
@click.argument("finding_id")
@click.argument("accepted", type=click.Choice(["accept", "reject"]))
@click.option("--repo", default="default", help="Repository identifier.")
@click.option("--reason", default="", help="Reason for the decision.")
def feedback(finding_id: str, accepted: str, repo: str, reason: str):
    """Submit feedback on a finding.

    Example: ci-optimizer feedback cache-lint accept --reason "Saved 30s"
    """
    store = FeedbackStore()
    entry = store.submit(
        repo=repo,
        finding_id=finding_id,
        accepted=(accepted == "accept"),
        reason=reason if reason else None,
    )

    action = "Accepted" if entry.accepted else "Rejected"
    click.echo(f"{action}: {finding_id}")

    stats = store.get_stats(repo)
    click.echo(f"Total feedback: {stats['total_feedback']} ({stats['accepted']} accepted, {stats['rejected']} rejected)")


@main.command()
def rules():
    """List all available optimization rules."""
    from src.rules import ALL_RULES

    rule_descriptions = {
        "check_missing_cache": ("Missing Dependency Cache", "critical", "Detects jobs installing dependencies without caching."),
        "check_install_commands": ("Inefficient Install Commands", "warning", "Flags npm install instead of npm ci."),
        "check_missing_concurrency": ("Missing Concurrency Controls", "warning", "Flags workflows without concurrency groups."),
        "check_outdated_actions": ("Outdated Action Versions", "info", "Catches old action versions."),
        "check_sequential_jobs": ("Sequential Parallelizable Jobs", "warning", "Identifies jobs that could run in parallel."),
        "check_redundant_builds": ("Redundant Build Steps", "critical", "Detects duplicate build commands across jobs."),
        "check_missing_sharding": ("Missing Test Sharding", "info", "Suggests matrix strategies for test jobs."),
    }

    click.echo("CI Optimization Rules")
    click.echo("=" * 40)
    click.echo()

    for rule_fn in ALL_RULES:
        name = rule_fn.__name__
        if name in rule_descriptions:
            title, severity, desc = rule_descriptions[name]
            badge = {"critical": "[!!]", "warning": "[!]", "info": "[i]"}[severity]
            click.echo(f"  {badge} {title}")
            click.echo(f"      {desc}")
            click.echo()


if __name__ == "__main__":
    main()