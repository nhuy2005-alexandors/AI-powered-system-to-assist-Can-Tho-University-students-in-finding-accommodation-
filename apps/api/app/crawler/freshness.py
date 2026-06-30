import math
from datetime import datetime, timezone

# T11: sau bao nhiêu chu kỳ full không thấy lại → expired (≈ số ngày)
MISS_THRESHOLD = 2
# hằng số phân rã freshness theo tuổi last_seen (ngày)
DECAY_DAYS = 7.0


def freshness_score(last_seen: datetime, now: datetime | None = None) -> float:
    """exp(-age_days / DECAY_DAYS), kẹp [0, 1]. Tin vừa thấy = 1.0."""
    now = now or datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - last_seen).total_seconds() / 86400.0)
    return round(math.exp(-age_days / DECAY_DAYS), 4)


def should_expire(miss_count: int) -> bool:
    return miss_count >= MISS_THRESHOLD


def next_status(miss_count: int, current: str) -> str:
    """Quyết status mới. P2: không bao giờ DELETE, chỉ chuyển 'expired'."""
    if current == "flagged":
        return current  # flagged do risk/report giữ nguyên, Admin xử lý
    return "expired" if should_expire(miss_count) else "active"
