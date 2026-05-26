"""LLM-powered deep analysis layer using Claude API."""

import os
import json
from typing import Optional

from src.models import AnalysisReport


def is_llm_available() -> bool:
    """Check if the Claude API key is configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def get_llm_analysis(
    yaml_content: str,
    report: AnalysisReport,
) -> Optional[dict]:
    """Generate LLM-powered deep analysis of a workflow.

    Takes the rule engine's findings plus raw YAML and produces:
    - Natural language explanations with estimated time savings
    - Structural suggestions the rules can't catch
    - A fully optimized YAML output
    - Priority ordering by estimated impact

    Args:
        yaml_content: The raw workflow YAML.
        report: The rule engine's analysis report.

    Returns:
        Dict with LLM analysis results, or None if API key is not set.
    """
    if not is_llm_available():
        return None

    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic()

    # Build a summary of rule findings for context
    findings_summary = "\n".join(
        f"- [{f.severity.value.upper()}] {f.title}: {f.description}"
        for f in report.findings
    )

    prompt = f"""You are a CI/CD optimization expert. Analyze this GitHub Actions workflow and the rule-based findings below.

## Workflow YAML

```yaml
{yaml_content}
```

## Rule Engine Findings

{findings_summary}

## Your Task

Provide a deep analysis in the following JSON format (respond with ONLY valid JSON, no markdown fences):

{{
    "narrative": "A 2-3 paragraph explanation of the workflow's overall health, key bottlenecks, and recommended optimization strategy.",
    "estimated_time_savings_pct": 65,
    "priority_order": ["finding-id-1", "finding-id-2"],
    "structural_suggestions": [
        {{
            "title": "Extract Reusable Composite Action",
            "description": "Why and how to do it",
            "impact": "high"
        }}
    ],
    "optimized_workflow": "The fully optimized YAML as a string"
}}

Focus on:
1. Estimated percentage reduction in total CI time
2. Which optimizations to apply first for maximum impact
3. Structural improvements the rule engine missed (composite actions, reusable workflows, artifact strategies)
4. A fully working optimized YAML that applies all suggestions
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse the response
    response_text = message.content[0].text

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # If Claude wrapped it in markdown fences, strip them
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "narrative": response_text,
                "error": "Could not parse structured response",
            }