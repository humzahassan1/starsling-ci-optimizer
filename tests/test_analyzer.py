"""Tests for the core analysis engine."""

import pytest
from src.analyzer import analyze_workflow, parse_workflow


def test_parse_valid_yaml():
    yaml_content = "name: CI\non: push\njobs:\n  test:\n    steps:\n      - run: echo hi"
    result = parse_workflow(yaml_content)
    assert isinstance(result, dict)
    assert result["name"] == "CI"


def test_parse_invalid_yaml():
    with pytest.raises(ValueError, match="Invalid YAML"):
        parse_workflow(":\n  :\n    - [invalid")


def test_analyze_missing_jobs_key():
    with pytest.raises(ValueError, match="no 'jobs' key"):
        analyze_workflow("name: CI\non: push")


def test_analyze_produces_report():
    yaml_content = """
name: CI
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: npm test
"""
    report = analyze_workflow(yaml_content, "test.yml", use_llm=False)
    assert report.workflow_name == "test.yml"
    assert len(report.findings) > 0


def test_analyze_clean_workflow_minimal_findings():
    yaml_content = """
name: CI
on: push
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          cache: npm
      - run: npm ci
      - run: echo "no tests yet"
"""
    report = analyze_workflow(yaml_content, "clean.yml", use_llm=False)
    # Should have very few or no findings
    assert report.summary["critical"] == 0