from __future__ import annotations

from fastapi import HTTPException

from .repo import RiskRepository
from .schemas import RiskAssessment, RiskBatchResponse, RiskSignal
from .scoring import MODEL_VERSION, ScoreResult, score_listing


class RiskService:
    def __init__(self, repo: RiskRepository):
        self.repo = repo

    @staticmethod
    def _response(listing_id: int, result: ScoreResult, persisted: bool) -> RiskAssessment:
        return RiskAssessment(
            listing_id=listing_id,
            risk_score=result.score,
            risk_level=result.level,
            risk_reasons=result.reasons,
            signals=[
                RiskSignal(code=item.code, message=item.message, weight=item.weight)
                for item in result.signals
            ],
            model_version=MODEL_VERSION,
            evaluated_at=result.evaluated_at,
            persisted=persisted,
        )

    def assess(self, listing_id: int, *, persist: bool) -> RiskAssessment:
        listing = self.repo.get_listing(listing_id)
        if listing is None:
            raise HTTPException(404, "Không tìm thấy tin nhà trọ")
        median = self.repo.district_median_price(listing)
        result = score_listing(listing, district_median_price=median)
        if persist:
            self.repo.save(listing_id, result)
        return self._response(listing_id, result, persist)

    def assess_pending(self, limit: int) -> RiskBatchResponse:
        counts = {"safe": 0, "caution": 0, "suspicious": 0}
        failed: list[int] = []
        for listing_id in self.repo.pending_ids(limit):
            try:
                result = self.assess(listing_id, persist=True)
                counts[result.risk_level] += 1
            except Exception:
                failed.append(listing_id)
        return RiskBatchResponse(
            processed=sum(counts.values()),
            safe=counts["safe"],
            caution=counts["caution"],
            suspicious=counts["suspicious"],
            failed_listing_ids=failed,
        )
