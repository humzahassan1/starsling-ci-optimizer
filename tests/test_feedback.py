"""Tests for the feedback store."""

import pytest
import tempfile
from pathlib import Path

from src.feedback import FeedbackStore


@pytest.fixture
def store(tmp_path):
    """Create a feedback store with a temporary directory."""
    return FeedbackStore(feedback_dir=tmp_path)


def test_submit_accepted(store):
    entry = store.submit("myrepo", "cache-lint", accepted=True, reason="Saved 30s")
    assert entry.accepted is True
    assert entry.finding_id == "cache-lint"


def test_submit_rejected(store):
    entry = store.submit("myrepo", "shard-test", accepted=False, reason="Too complex")
    assert entry.accepted is False


def test_stats_tracking(store):
    store.submit("myrepo", "cache-lint", accepted=True)
    store.submit("myrepo", "cache-build", accepted=True)
    store.submit("myrepo", "shard-test", accepted=False)

    stats = store.get_stats("myrepo")
    assert stats["total_feedback"] == 3
    assert stats["accepted"] == 2
    assert stats["rejected"] == 1


def test_rejection_patterns(store):
    store.submit("myrepo", "shard-test", accepted=False)
    store.submit("myrepo", "shard-build", accepted=False)
    store.submit("myrepo", "cache-lint", accepted=True)

    patterns = store.get_rejection_patterns("myrepo")
    assert patterns["shard"] == 1.0  # 100% rejected
    assert "cache" not in patterns or patterns["cache"] == 0.0


def test_should_deprioritize(store):
    # Reject shard findings 3 times
    store.submit("myrepo", "shard-test", accepted=False)
    store.submit("myrepo", "shard-build", accepted=False)
    store.submit("myrepo", "shard-deploy", accepted=False)

    assert store.should_deprioritize("myrepo", "shard") is True
    assert store.should_deprioritize("myrepo", "cache") is False


def test_empty_repo_stats(store):
    stats = store.get_stats("nonexistent")
    assert stats["total_feedback"] == 0