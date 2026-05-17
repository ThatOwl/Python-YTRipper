import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import utility.preferences as preferences

from ..runtime.package_builder import TaggingQueueStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TaggingReviewStore:
    """Persist lightweight operator review decisions and tag overrides."""

    RETRYABLE_STATES = ("failed", "skipped", "enriched")

    def __init__(self, base_dir: Path | str | None = None):
        if base_dir is None:
            base_dir = preferences.PROJECT_ROOT / "runtime" / "tagging"
        self.base_dir = Path(base_dir)
        self.review_dir = self.base_dir / "reviews"

    def ensure_review_dir(self) -> Path:
        self.review_dir.mkdir(parents=True, exist_ok=True)
        return self.review_dir

    def read_review(self, job_id: str) -> dict[str, Any] | None:
        path = self.review_dir / f"{job_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    def list_reviews(self) -> list[dict[str, Any]]:
        if not self.review_dir.exists():
            return []
        reviews: list[dict[str, Any]] = []
        for path in sorted(self.review_dir.glob("*.json")):
            review = self.read_review(path.stem)
            if review:
                reviews.append(review)
        reviews.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return reviews

    def save_override(
        self,
        job_id: str,
        override_fields: dict[str, Any],
        note: str = "",
    ) -> dict[str, Any]:
        review = self.read_review(job_id) or {"job_id": job_id, "created_at": _utc_now_iso()}
        review["override_fields"] = {
            key: value
            for key, value in override_fields.items()
            if value not in (None, "")
        }
        review["note"] = note
        review["decision"] = "override_saved"
        review["updated_at"] = _utc_now_iso()
        self._write_review(job_id, review)
        return review

    def approve_candidate(self, job_id: str, note: str = "") -> dict[str, Any]:
        review = self.read_review(job_id) or {"job_id": job_id, "created_at": _utc_now_iso()}
        review["decision"] = "approved"
        review["note"] = note
        review["updated_at"] = _utc_now_iso()
        self._write_review(job_id, review)
        return review

    def reject_candidate(self, job_id: str, reason: str = "") -> dict[str, Any]:
        review = self.read_review(job_id) or {"job_id": job_id, "created_at": _utc_now_iso()}
        review["decision"] = "rejected"
        review["note"] = reason
        review["updated_at"] = _utc_now_iso()
        self._write_review(job_id, review)
        return review

    def list_review_candidates(
        self,
        queue_store: TaggingQueueStore,
        *,
        session_id: str | None = None,
        states: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        target_states = states or self.RETRYABLE_STATES
        candidates: list[dict[str, Any]] = []

        for queue_state in ("failed", "done"):
            for payload in queue_store.list_state_payloads(queue_state):
                payload_state = str(payload.get("state", "") or "")
                if payload_state not in target_states:
                    continue
                if session_id and str(payload.get("session_id", "") or "") != session_id:
                    continue

                summary = queue_store.summarize_package(payload)
                review = self.read_review(str(payload.get("job_id", "") or ""))
                summary["review_decision"] = (review or {}).get("decision", "")
                summary["review_note"] = (review or {}).get("note", "")
                summary["override_saved"] = bool((review or {}).get("override_fields"))
                candidates.append(summary)

        candidates.sort(
            key=lambda item: (
                str(item.get("last_transition_at", "")),
                int(item.get("sequence_no", 0) or 0),
            ),
            reverse=True,
        )
        return candidates

    def _write_review(self, job_id: str, review: dict[str, Any]) -> None:
        self.ensure_review_dir()
        with open(self.review_dir / f"{job_id}.json", "w", encoding="utf-8") as handle:
            json.dump(review, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
