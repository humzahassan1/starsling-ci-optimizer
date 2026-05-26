"""Tests for the rule-based analysis engine."""

import pytest
from src.rules.caching import check_missing_cache
from src.rules.install import check_install_commands
from src.rules.concurrency import check_missing_concurrency
from src.rules.actions import check_outdated_actions
from src.rules.parallelization import check_sequential_jobs
from src.rules.redundancy import check_redundant_builds
from src.rules.sharding import check_missing_sharding


# --- Caching ---

def test_missing_cache_detected():
    workflow = {
        "jobs": {
            "test": {
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"run": "npm install"},
                    {"run": "npm test"},
                ]
            }
        }
    }
    findings = check_missing_cache(workflow)
    assert len(findings) == 1
    assert findings[0].severity.value == "critical"
    assert findings[0].category.value == "caching"


def test_cache_present_no_finding():
    workflow = {
        "jobs": {
            "test": {
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"uses": "actions/setup-node@v4", "with": {"cache": "npm"}},
                    {"run": "npm ci"},
                    {"run": "npm test"},
                ]
            }
        }
    }
    findings = check_missing_cache(workflow)
    assert len(findings) == 0


# --- Install ---

def test_npm_install_flagged():
    workflow = {
        "jobs": {
            "build": {
                "steps": [
                    {"run": "npm install"},
                ]
            }
        }
    }
    findings = check_install_commands(workflow)
    assert len(findings) == 1
    assert "npm ci" in findings[0].after_yaml


def test_npm_ci_not_flagged():
    workflow = {
        "jobs": {
            "build": {
                "steps": [
                    {"run": "npm ci"},
                ]
            }
        }
    }
    findings = check_install_commands(workflow)
    assert len(findings) == 0


# --- Concurrency ---

def test_missing_concurrency_detected():
    workflow = {
        "on": {"push": {"branches": ["main"]}},
        "jobs": {"test": {"steps": []}},
    }
    findings = check_missing_concurrency(workflow)
    assert len(findings) == 1
    assert findings[0].category.value == "concurrency"


def test_concurrency_present_no_finding():
    workflow = {
        "on": {"push": {"branches": ["main"]}},
        "concurrency": {"group": "ci-${{ github.ref }}"},
        "jobs": {"test": {"steps": []}},
    }
    findings = check_missing_concurrency(workflow)
    assert len(findings) == 0


# --- Actions ---

def test_outdated_action_detected():
    workflow = {
        "jobs": {
            "test": {
                "steps": [
                    {"uses": "actions/checkout@v3"},
                ]
            }
        }
    }
    findings = check_outdated_actions(workflow)
    assert len(findings) == 1
    assert "v4" in findings[0].after_yaml


def test_current_action_no_finding():
    workflow = {
        "jobs": {
            "test": {
                "steps": [
                    {"uses": "actions/checkout@v4"},
                ]
            }
        }
    }
    findings = check_outdated_actions(workflow)
    assert len(findings) == 0


# --- Parallelization ---

def test_sequential_jobs_detected():
    workflow = {
        "jobs": {
            "lint": {
                "steps": [{"run": "npm run lint"}],
            },
            "test": {
                "needs": "lint",
                "steps": [{"run": "npm test"}],
            },
        }
    }
    findings = check_sequential_jobs(workflow)
    assert any(f.category.value == "parallelization" for f in findings)


# --- Redundancy ---

def test_redundant_build_detected():
    workflow = {
        "jobs": {
            "build": {
                "steps": [{"run": "npm run build"}],
            },
            "deploy": {
                "steps": [{"run": "npm run build"}, {"run": "npm run deploy"}],
            },
        }
    }
    findings = check_redundant_builds(workflow)
    assert len(findings) == 1
    assert findings[0].severity.value == "critical"


def test_single_build_no_finding():
    workflow = {
        "jobs": {
            "build": {
                "steps": [{"run": "npm run build"}],
            },
        }
    }
    findings = check_redundant_builds(workflow)
    assert len(findings) == 0


# --- Sharding ---

def test_missing_sharding_detected():
    workflow = {
        "jobs": {
            "test": {
                "steps": [
                    {"run": "npm test"},
                ]
            }
        }
    }
    findings = check_missing_sharding(workflow)
    assert len(findings) == 1
    assert findings[0].category.value == "sharding"


def test_matrix_present_no_finding():
    workflow = {
        "jobs": {
            "test": {
                "strategy": {"matrix": {"shard": [1, 2, 3]}},
                "steps": [
                    {"run": "npm test"},
                ]
            }
        }
    }
    findings = check_missing_sharding(workflow)
    assert len(findings) == 0