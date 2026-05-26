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
This is the most important file in the repo — it's what Daniel and Yonas will actually read. Create README.md in the project root:
markdown# StarSling CI Optimizer

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
# Analyze a workflow file
python -m src.cli analyze .github/workflows/ci.yml

# Rule engine only (no LLM)
python -m src.cli analyze .github/workflows/ci.yml --no-llm

# Output as JSON
python -m src.cli analyze .github/workflows/ci.yml --json

# List all rules
python -m src.cli rules

# Submit feedback
python -m src.cli feedback cache-lint accept --reason "Saved 30s"
python -m src.cli feedback shard-test reject --reason "Suite too small"
```

### MCP Server

```bash
# Run the MCP server
python -m src.server
```

The server exposes four tools via the Model Context Protocol:

| Tool | Description |
|------|-------------|
| `analyze_workflow` | Full analysis on a workflow YAML string |
| `get_optimization_detail` | Deep dive on a specific finding by ID |
| `list_rules` | Show all optimization rules with severity levels |
| `submit_feedback` | Accept/reject a suggestion with optional reason |

### Example — Deliberately Bad Workflow

Running against `examples/unoptimized-nextjs.yml` (a workflow with 8+ intentional anti-patterns):
## Architecture
src/
├── server.py          # MCP server — exposes tools via Model Context Protocol
├── analyzer.py        # Core engine — parses YAML, runs rules, assembles report
├── rules/             # Rule modules — each is a standalone function
│   ├── caching.py     # Dependency caching detection
│   ├── install.py     # Install command optimization
│   ├── concurrency.py # Concurrency group detection
│   ├── actions.py     # Action version checking
│   ├── parallelization.py  # Sequential job detection
│   ├── redundancy.py  # Duplicate build detection
│   └── sharding.py    # Test sharding suggestions
├── llm.py             # Claude API integration for deep analysis
├── feedback.py        # Feedback loop / memory store
├── models.py          # Data models (Finding, Report, FeedbackEntry)
└── cli.py             # CLI entry point

### Design Decisions

**Two-layer analysis over pure LLM.** An LLM-only approach would work but has downsides: it's slow, costs money per call, and produces non-deterministic output. The rule engine handles the 80% case instantly and for free. The LLM layer adds the 20% that requires reasoning — structural suggestions, priority ordering, and generating a complete optimized workflow. This mirrors how StarSling's own agents likely work: fast heuristics for known patterns, deeper analysis for novel situations.

**Rules as standalone functions.** Each rule is a pure function: `dict → list[Finding]`. No shared state, no side effects, independently testable. Adding a new rule means writing one function and adding it to `ALL_RULES`. This matters because CI best practices evolve — new rules should be trivial to add.

**Feedback as deprioritization, not deletion.** Rejected suggestions aren't removed from future analyses — they're deprioritized. The user might reject test sharding today because their suite is small, but revisit it when the suite grows. The system remembers preferences without being permanently opinionated.

**MCP as the interface.** MCP is how AI agents talk to external tools. Exposing the optimizer as an MCP server means any MCP-compatible agent (Claude, Cursor, custom agents) can use it as a tool in a larger workflow. This is exactly how StarSling's architecture works — agents that orchestrate tools to analyze and optimize CI.

**Code quality as a practice, not a checkbox.** This project was informed by Mitchell Hashimoto's concept of "anti-slop sessions" - the cleanup phase after AI-assisted coding where you force yourself to understand every line, reorganize for clarity, and document decisions. Daniel [wrote about this](https://www.linkedin.com/in/worku/) as a practice he values. Every module in this codebase went through that pass: no dead code, no unexplained abstractions, no "it works so don't touch it" corners. The rule functions are deliberately simple, not because the problem is simple, but because the cleanup pass kept asking "does this need to be here?"

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# 24 tests covering:
# - Each rule (positive and negative cases)
# - YAML parsing and error handling
# - Analysis engine integration
# - Feedback store operations
```

## What I'd Build Next

With more time (or on the job), the natural extensions are:

1. **GitHub API integration** — Pull workflow files and run logs directly from repositories instead of requiring manual YAML input. Run logs contain timing data that would make impact estimates precise rather than heuristic.

2. **Auto-PR generation** — After analysis, automatically open a PR with the optimized workflow. This is StarSling's core product loop: analyze → suggest → apply.

3. **Telemetry analysis** — Parse runner telemetry (CPU, memory, disk I/O) to catch performance issues the YAML alone can't reveal — like a test suite that's CPU-bound and would benefit from a larger runner.

4. **Composite action extraction** — When multiple jobs share 80%+ of their setup steps, automatically generate a reusable composite action and refactor the workflow to use it.

5. **Historical trend tracking** — Track CI performance over time per repository. Show a dashboard of "your CI was 45% faster this month because you accepted these 3 suggestions."

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3.11+ | Matches StarSling's backend stack |
| MCP SDK | `mcp` Python SDK | Official MCP server implementation |
| LLM | Claude API (claude-sonnet-4-20250514) | Cost-effective for analysis tasks |
| YAML Parsing | PyYAML | Standard Python YAML parser |
| CLI | Click | Clean CLI interface |
| Feedback Store | JSON files | Simple, no external dependencies, inspectable |
| Testing | pytest | Standard Python testing |

## License

MIT
