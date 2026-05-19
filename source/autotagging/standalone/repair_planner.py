from typing import Any

from autotagging.runtime_tagging.package_builder import TaggingQueueStore
from autotagging.standalone.review_store import TaggingReviewStore


class TaggingRepairPlanner:
    """Generate conservative operator suggestions from queue and review state."""

    def __init__(
        self,
        queue_store: TaggingQueueStore,
        review_store: TaggingReviewStore,
    ):
        self.queue_store = queue_store
        self.review_store = review_store

    def plan_session_repairs(self, session_id: str) -> list[dict[str, Any]]:
        candidates = self.review_store.list_review_candidates(
            self.queue_store,
            session_id=session_id,
        )
        plans: list[dict[str, Any]] = []
        for candidate in candidates:
            plans.append(
                {
                    "scope": "session",
                    "target_id": session_id,
                    "job_id": candidate.get("job_id", ""),
                    "current_state": candidate.get("state", ""),
                    "suggested_action": self._suggest_action(candidate),
                    "reason": self._suggest_reason(candidate),
                    "review_decision": candidate.get("review_decision", ""),
                    "override_saved": candidate.get("override_saved", False),
                }
            )
        return plans

    def plan_queue_maintenance(self) -> list[dict[str, Any]]:
        snapshot = self.queue_store.build_queue_snapshot(limit_per_state=0)
        counts = snapshot.get("counts", {})
        plans: list[dict[str, Any]] = []
        for state_name in ("failed", "processing", "pending"):
            count = int(counts.get(state_name, 0) or 0)
            if count <= 0:
                continue
            action = {
                "failed": "review_and_retry",
                "processing": "check_for_stale_worker",
                "pending": "run_worker",
            }[state_name]
            reason = {
                "failed": "failed packages need operator review or manual retry",
                "processing": "packages remain in processing and may indicate an interrupted worker",
                "pending": "prepared packages are waiting for worker processing",
            }[state_name]
            plans.append(
                {
                    "scope": "queue",
                    "target_id": state_name,
                    "job_id": "",
                    "current_state": state_name,
                    "suggested_action": action,
                    "reason": reason,
                    "review_decision": "",
                    "override_saved": False,
                }
            )
        return plans

    def suggest_follow_up_actions(self, job_id: str) -> list[str]:
        review = self.review_store.read_review(job_id) or {}
        for queue_state in ("failed", "done", "pending", "processing"):
            for payload in self.queue_store.list_state_payloads(queue_state):
                if str(payload.get("job_id", "") or "") != job_id:
                    continue
                state = str(payload.get("state", "") or "")
                if state == "failed":
                    return ["inspect events", "save override", "retry-run"]
                if state in {"skipped", "enriched"}:
                    if review.get("override_fields"):
                        return ["retry-run"]
                    return ["inspect candidate", "save override", "retry"]
                if state == "written":
                    return ["inspect tags", "no action needed"]
                if state == "prepared":
                    return ["run worker"]
        return ["job not found"]

    @staticmethod
    def _suggest_action(candidate: dict[str, Any]) -> str:
        state = str(candidate.get("state", "") or "")
        if state == "failed":
            return "inspect_then_retry"
        if candidate.get("override_saved"):
            return "retry_run_with_override_review"
        if state in {"skipped", "enriched"}:
            return "review_candidate_then_retry"
        return "inspect"

    @staticmethod
    def _suggest_reason(candidate: dict[str, Any]) -> str:
        state = str(candidate.get("state", "") or "")
        if state == "failed":
            return "worker failed to complete package processing"
        if state == "skipped":
            return "candidate was not safe enough for automatic tag writes"
        if state == "enriched":
            return "enrichment found a match but package still needs an operator pass"
        return "package needs operator inspection"
