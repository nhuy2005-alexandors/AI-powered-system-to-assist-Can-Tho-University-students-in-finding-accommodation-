import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.engine import Engine

from .pipeline import run_source
from .repo import ListingRepo

log = logging.getLogger("crawler.scheduler")

# Nguồn đang hoạt động
ENABLED_SOURCES = [
    "phongtro123",
    "tromoi",
    "mogi",
    "bds123",
    "nhadatcantho",
    "nhadatcantho247"
]


async def _job(engine: Engine, source: str, mode: str) -> None:
    repo = ListingRepo(engine)
    try:
        await run_source(source, mode, repo)
        
        # Chạy pipeline làm sạch sau khi crawl xong
        from app.cleaner.pipeline import run_cleaner
        run_cleaner(engine)
        
    except Exception:  # noqa: BLE001 — job không được làm chết scheduler
        log.exception("crawl job failed source=%s mode=%s", source, mode)


def build_scheduler(engine: Engine) -> AsyncIOScheduler:
    """
    Near-fresh batch, KHÔNG real-time:
      - incremental mỗi 5h (trang 1-2): bắt tin mới nhanh, ít request
      - full sweep 3h sáng: quét sâu + đánh dấu expired
    """
    sched = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
    for source in ENABLED_SOURCES:
        sched.add_job(
            _job, CronTrigger(hour="*/5"), args=[engine, source, "incremental"],
            id=f"{source}-incremental", max_instances=1, coalesce=True,
        )
        sched.add_job(
            _job, CronTrigger(hour=3, minute=0), args=[engine, source, "full"],
            id=f"{source}-full", max_instances=1, coalesce=True,
        )
    return sched
