# StarSling CI Optimizer

An MCP server that analyzes GitHub Actions workflow YAML files and generates actionable optimization suggestions. Built as a two-layer analysis engine: deterministic rules for instant, free analysis + optional LLM-powered deep insights via Claude.

## Why This Exists

CI is the tax every team pays on every push. Most workflows are written once and never optimized — they accumulate anti-patterns that silently waste minutes on every run. Missing dependency caching alone can add 30-90 seconds per job, and when you have 5 jobs running sequentially that could run in parallel, those minutes compound fast.

StarSling's agents solve this at scale — analyzing workflows, run logs, and machine telemetry to continuously optimize CI. This project is a focused implementation of that same core loop: parse a workflow, identify anti-patterns, suggest fixes, and learn from feedback.

## How It Works

### Layer 1: Rule-Based Analysis (deterministic, instant, free)

Seven codified heuristics that catch the most common CI anti-patterns:

| Rule | Severity | What It Catches |
|------|----------|----------------|
| Missing Dependency Cache | Critical | Jobs installing packages without caching — the #1 CI slowdown |
| Redundant Build Steps | Critical | Same build command running in multiple jobs |
| Inefficient Install Commands | Warning | `npm install` instead of `npm ci`, missing `--frozen-lockfile` |
| Missing Concurrency Controls | Warning | No concurrency groups, so rapid pushes queue redundant runs |
| Sequential Parallelizable Jobs | Warning | Independent jobs chained via `needs` that could run in parallel |
| Outdated Action Versions | Info | Old action versions when newer ones are available |
| Missing Test Sharding | Info | Test jobs that could benefit from matrix strategies |

Each rule produces structured findings with severity, description, affected jobs, and before/after YAML snippets showing the exact fix.

### Layer 2: LLM-Powered Deep Analysis (optional)

When an Anthropic API key is configured, the analyzer sends the workflow + rule findings to Claude for deeper structural analysis:

- Natural language explanations with estimated time savings
- Structural suggestions rules can't catch (e.g., "extract a reusable composite action")
- A fully optimized YAML that applies all suggestions at once
- Priority ordering by estimated impact

Without an API key, the server gracefully degrades to rule-engine-only mode.

### Feedback Loop

A JSON-based feedback store tracks which suggestions are accepted or rejected per repository. When a user consistently rejects a certain type of optimization (e.g., test sharding), future analyses deprioritize it. This is the closed-loop mechanism — the system learns from its interactions.

## Quick Start

### Prerequisites

- Python 3.11+
- `pip install pyyaml click anthropic mcp[cli]`

### CLI Usage

```bash