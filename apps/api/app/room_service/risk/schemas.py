from datetime import datetime

from pydantic import BaseModel, Field


class RiskSignal(BaseModel):
    code: str
    message: str
    weight: float = Field(ge=0, le=1)


class RiskAssessment(BaseModel):
    listing_id: int
    risk_score: float = Field(ge=0, le=1)
    risk_level: str
    risk_reasons: list[str] = Field(default_factory=list)
    signals: list[RiskSignal] = Field(default_factory=list)
    model_version: str
    evaluated_at: datetime
    persisted: bool = False


class RiskBatchResponse(BaseModel):
    processed: int
    safe: int
    caution: int
    suspicious: int
    failed_listing_ids: list[int] = Field(default_factory=list)
