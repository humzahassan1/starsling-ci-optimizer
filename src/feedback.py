"""Feedback loop — tracks accepted/rejected suggestions to improve future analyses."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.models import FeedbackEntry


DEFAULT_FEEDBACK_DIR = Path("feedback")


class FeedbackStore:
    """JSON-based feedback store that tracks suggestion outcomes per repository."""

    def __init__(self, feedback_dir: Path = DEFAULT_FEEDBACK_DIR):
        self.feedback_dir = feedback_dir
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def _get_repo_path(self, repo: str) -> Path:
        """Get the feedback file path for a repository."""
        # Sanitize repo name for use as filename
        safe_name = repo.replace("/", "_").replace("\\", "_")
        return self.feedback_dir / f"{safe_name}.json"

    def _load_repo_feedback(self, repo: str) -> dict:
        """Load existing feedback for a repository."""
        path = self._get_repo_path(repo)
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return {"repo": repo, "entries": [], "stats": {}}

    def _save_repo_feedback(self, repo: str, data: dict) -> None:
        """Save feedback data for a repository."""
        path = self._get_repo_path(repo)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def submit(
        self,
        repo: str,
        finding_id: str,
        accepted: bool,
        reason: Optional[str] = None,
    ) -> FeedbackEntry:
        """Record feedback for a specific finding.

        Args:
            repo: Repository identifier (e.g., 'myorg/myrepo').
            finding_id: The ID of the finding being reviewed.
            accepted: Whether the suggestion was accepted or rejected.
            reason: Optional reason for the decision.

        Returns:
            The created FeedbackEntry.
        """
        entry = FeedbackEntry(
            finding_id=finding_id,
            accepted=accepted,
            reason=reason,
            timestamp=datetime.now(timezone.utc),
        )

        data = self._load_repo_feedback(repo)
        data["entries"].append(entry.to_dict())

        # Update aggregate stats
        rule_name = finding_id.rsplit("-", 1)[0]
        if rule_name not in data["stats"]:
            data["stats"][rule_name] = {"accepted": 0, "rejected": 0}

        if accepted:
            data["stats"][rule_name]["accepted"] += 1
        else:
            data["stats"][rule_name]["rejected"] += 1

        self._save_repo_feedback(repo, data)
        return entry

    def get_rejection_patterns(self, repo: str) -> dict[str, float]:
        """Get rejection rates by rule type for a repository.

        Returns a dict mapping rule names to rejection rates (0.0 to 1.0).
        Rules with high rejection rates should be deprioritized.
        """
        data = self._load_repo_feedback(repo)
        patterns = {}

        for rule_name, stats in data.get("stats", {}).items():
            total = stats["accepted"] + stats["rejected"]
            if total > 0:
                patterns[rule_name] = stats["rejected"] / total

        return patterns

    def get_stats(self, repo: str) -> dict:
        """Get aggregate feedback statistics for a repository."""
        data = self._load_repo_feedback(repo)
        entries = data.get("entries", [])

        return {
            "repo": repo,
            "total_feedback": len(entries),
            "accepted": sum(1 for e in entries if e["accepted"]),
            "rejected": sum(1 for e in entries if not e["accepted"]),
            "rule_stats": data.get("stats", {}),
        }

    def should_deprioritize(self, repo: str, rule_name: str, threshold: float = 0.7) -> bool:
        """Check if a rule should be deprioritized based on past rejections.

        Args:
            repo: Repository identifier.
            rule_name: The rule to check.
            threshold: Rejection rate above which to deprioritize (default 70%).

        Returns:
            True if the rule has been rejected frequently enough to deprioritize.
        """
        patterns = self.get_rejection_patterns(repo)
        return patterns.get(rule_name, 0.0) >= threshold