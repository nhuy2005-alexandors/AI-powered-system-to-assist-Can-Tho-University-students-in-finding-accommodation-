from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReportReason(str, Enum):
    wrong_price = "wrong_price"
    expired = "expired"
    scam = "scam"
    other = "other"


class ReportStatus(str, Enum):
    pending = "pending"
    reviewed = "reviewed"
    dismissed = "dismissed"


class ReportCreate(BaseModel):
    reason: ReportReason
    note: str | None = Field(default=None, max_length=1000)


class ReportOut(BaseModel):
    id: int
    listing_id: int
    reporter_id: int | None
    reason: ReportReason
    note: str | None = None
    status: ReportStatus
    created_at: datetime
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    resolution_note: str | None = None


class AdminReportItem(ReportOut):
    reporter_email: str | None = None
    reporter_name: str | None = None
    listing_title: str
    listing_status: str
    listing_price: int | None = None
    listing_address: str | None = None
    risk_score: float | None = None
    risk_level: str = "unknown"
    risk_reasons: list[str] = Field(default_factory=list)
    open_report_count: int = 0


class AdminReportList(BaseModel):
    total: int
    items: list[AdminReportItem]


class ModerationAction(str, Enum):
    dismiss = "dismiss"
    flag = "flag"
    hide = "hide"


class ModerateReportIn(BaseModel):
    action: ModerationAction
    note: str | None = Field(default=None, max_length=1000)


class ModerationResult(BaseModel):
    listing_id: int
    action: ModerationAction
    resolved_reports: int
    listing_status: str
    risk_score: float | None = None
    risk_level: str | None = None


class AdminDashboardSummary(BaseModel):
    total_listings: int
    active_listings: int
    flagged_listings: int
    hidden_listings: int
    pending_reports: int
    reporting_users: int
    total_users: int


class AdminListingStatus(str, Enum):
    active = "active"
    expired = "expired"
    flagged = "flagged"
    hidden = "hidden"


class AdminListingStatusIn(BaseModel):
    status: AdminListingStatus


class AdminListingItem(BaseModel):
    id: int
    title: str
    price: int | None = None
    address: str | None = None
    district: str | None = None
    source: str
    status: AdminListingStatus
    risk_score: float | None = None
    risk_level: str = "unknown"
    risk_reasons: list[str] = Field(default_factory=list)
    report_count: int = 0
    posted_by: int | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class AdminListingList(BaseModel):
    total: int
    items: list[AdminListingItem]


class AdminUserItem(BaseModel):
    id: int
    email: str
    name: str | None = None
    role: str
    email_verified: bool = False
    created_at: datetime
    listing_count: int = 0
    report_count: int = 0


class AdminUserList(BaseModel):
    total: int
    items: list[AdminUserItem]
