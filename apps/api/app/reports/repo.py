from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..listings.schemas import risk_level
from .schemas import AdminListingItem, AdminReportItem, AdminUserItem, ReportOut


_REPORT_COLS = (
    "r.id, r.listing_id, r.reporter_id, r.reason, r.note, r.status, r.created_at, "
    "r.reviewed_by, r.reviewed_at, r.resolution_note"
)


def _report_out(row) -> ReportOut:
    return ReportOut(**dict(row))


def _admin_out(row) -> AdminReportItem:
    value = dict(row)
    value["risk_reasons"] = value.get("risk_reasons") or []
    value["risk_level"] = risk_level(value.get("risk_score"))
    return AdminReportItem(**value)


class ReportRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def get_reportable_listing(self, listing_id: int) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, posted_by, status::text AS status "
                    "FROM aggregated_listings WHERE id = :id"
                ),
                {"id": listing_id},
            ).mappings().first()
        return dict(row) if row else None

    def find_pending(self, listing_id: int, reporter_id: int) -> ReportOut | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {_REPORT_COLS} FROM reports r "
                    "WHERE r.listing_id = :listing_id AND r.reporter_id = :reporter_id "
                    "AND r.status = 'pending'"
                ),
                {"listing_id": listing_id, "reporter_id": reporter_id},
            ).mappings().first()
        return _report_out(row) if row else None

    def create(self, listing_id: int, reporter_id: int, reason: str, note: str | None) -> ReportOut:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO reports (listing_id, reporter_id, reason, note, status) "
                    "VALUES (:listing_id, :reporter_id, :reason, :note, 'pending') "
                    f"RETURNING {_REPORT_COLS.replace('r.', '')}"
                ),
                {
                    "listing_id": listing_id,
                    "reporter_id": reporter_id,
                    "reason": reason,
                    "note": note,
                },
            ).mappings().one()
            conn.execute(
                text("UPDATE aggregated_listings SET updated_at = now() WHERE id = :id"),
                {"id": listing_id},
            )
        return _report_out(row)

    def by_reporter(self, reporter_id: int) -> list[ReportOut]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT {_REPORT_COLS} FROM reports r WHERE r.reporter_id = :uid "
                    "ORDER BY r.created_at DESC"
                ),
                {"uid": reporter_id},
            ).mappings().all()
        return [_report_out(row) for row in rows]

    def admin_list(self, status: str | None, limit: int, offset: int) -> tuple[int, list[AdminReportItem]]:
        where = "WHERE r.status = :status" if status else ""
        params = {"status": status, "limit": limit, "offset": offset}
        with self.engine.connect() as conn:
            total = conn.execute(
                text(f"SELECT count(*) FROM reports r {where}"), params
            ).scalar_one()
            rows = conn.execute(
                text(
                    f"SELECT {_REPORT_COLS}, u.email AS reporter_email, u.name AS reporter_name, "
                    "l.title AS listing_title, l.status::text AS listing_status, "
                    "l.price AS listing_price, l.address AS listing_address, "
                    "l.risk_score, l.risk_reasons, "
                    "(SELECT count(*) FROM reports open_r WHERE open_r.listing_id = r.listing_id "
                    "AND open_r.status = 'pending') AS open_report_count "
                    "FROM reports r "
                    "JOIN aggregated_listings l ON l.id = r.listing_id "
                    "LEFT JOIN users u ON u.id = r.reporter_id "
                    f"{where} ORDER BY r.created_at DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            ).mappings().all()
        return int(total), [_admin_out(row) for row in rows]

    def moderate_listing_reports(
        self,
        report_id: int,
        admin_id: int,
        action: str,
        note: str | None,
    ) -> tuple[int, int, str] | None:
        report_status = "dismissed" if action == "dismiss" else "reviewed"
        listing_status = {"dismiss": "active", "flag": "flagged", "hide": "hidden"}[action]
        with self.engine.begin() as conn:
            report = conn.execute(
                text("SELECT listing_id, status FROM reports WHERE id = :id FOR UPDATE"),
                {"id": report_id},
            ).mappings().first()
            if report is None:
                return None
            listing_id = int(report["listing_id"])
            if report["status"] != "pending":
                return listing_id, 0, ""
            resolved = conn.execute(
                text(
                    "UPDATE reports SET status = :status, reviewed_by = :admin_id, "
                    "reviewed_at = now(), resolution_note = :note "
                    "WHERE listing_id = :listing_id AND status = 'pending'"
                ),
                {
                    "status": report_status,
                    "admin_id": admin_id,
                    "note": note,
                    "listing_id": listing_id,
                },
            ).rowcount
            conn.execute(
                text(
                    "UPDATE aggregated_listings SET status = CAST(:status AS listing_status), "
                    "updated_at = now() WHERE id = :listing_id"
                ),
                {"status": listing_status, "listing_id": listing_id},
            )
        return listing_id, int(resolved or 0), listing_status

    def set_listing_status(self, listing_id: int, status: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE aggregated_listings SET status = CAST(:status AS listing_status), "
                    "updated_at = now() WHERE id = :listing_id"
                ),
                {"status": status, "listing_id": listing_id},
            )

    def dashboard_summary(self) -> dict:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT count(*) AS total_listings, "
                    "count(*) FILTER (WHERE status = 'active') AS active_listings, "
                    "count(*) FILTER (WHERE status = 'flagged') AS flagged_listings, "
                    "count(*) FILTER (WHERE status = 'hidden') AS hidden_listings "
                    "FROM aggregated_listings"
                )
            ).mappings().one()
            report_row = conn.execute(
                text(
                    "SELECT count(*) FILTER (WHERE status = 'pending') AS pending_reports, "
                    "count(DISTINCT reporter_id) FILTER (WHERE status = 'pending') AS reporting_users "
                    "FROM reports"
                )
            ).mappings().one()
            total_users = conn.execute(text("SELECT count(*) FROM users")).scalar_one()
        return {**dict(row), **dict(report_row), "total_users": int(total_users)}

    def admin_listings(
        self,
        query: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[AdminListingItem]]:
        clauses: list[str] = []
        params: dict = {"limit": limit, "offset": offset}
        if query:
            clauses.append("(l.title ILIKE :query OR l.address ILIKE :query)")
            params["query"] = f"%{query}%"
        if status:
            clauses.append("l.status = CAST(:status AS listing_status)")
            params["status"] = status
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.engine.connect() as conn:
            total = conn.execute(
                text(f"SELECT count(*) FROM aggregated_listings l {where}"), params
            ).scalar_one()
            rows = conn.execute(
                text(
                    "SELECT l.id, l.title, l.price, l.address, l.district, l.source, "
                    "l.status::text AS status, l.risk_score, l.risk_reasons, l.posted_by, "
                    "l.first_seen, l.last_seen, "
                    "(SELECT count(*) FROM reports r WHERE r.listing_id = l.id "
                    "AND r.status IN ('pending', 'reviewed')) AS report_count "
                    f"FROM aggregated_listings l {where} "
                    "ORDER BY l.updated_at DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            ).mappings().all()
        items: list[AdminListingItem] = []
        for row in rows:
            value = dict(row)
            value["risk_reasons"] = value.get("risk_reasons") or []
            value["risk_level"] = risk_level(value.get("risk_score"))
            items.append(AdminListingItem(**value))
        return int(total), items

    def admin_listing(self, listing_id: int) -> AdminListingItem | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT l.id, l.title, l.price, l.address, l.district, l.source, "
                    "l.status::text AS status, l.risk_score, l.risk_reasons, l.posted_by, "
                    "l.first_seen, l.last_seen, "
                    "(SELECT count(*) FROM reports r WHERE r.listing_id = l.id "
                    "AND r.status IN ('pending', 'reviewed')) AS report_count "
                    "FROM aggregated_listings l WHERE l.id = :id"
                ),
                {"id": listing_id},
            ).mappings().first()
        if row is None:
            return None
        value = dict(row)
        value["risk_reasons"] = value.get("risk_reasons") or []
        value["risk_level"] = risk_level(value.get("risk_score"))
        return AdminListingItem(**value)

    def set_admin_listing_status(self, listing_id: int, status: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE aggregated_listings SET status = CAST(:status AS listing_status), "
                    "updated_at = now() WHERE id = :id"
                ),
                {"id": listing_id, "status": status},
            )
        return bool(result.rowcount)

    def admin_users(self, query: str | None, limit: int, offset: int) -> tuple[int, list[AdminUserItem]]:
        params: dict = {"limit": limit, "offset": offset}
        where = ""
        if query:
            where = "WHERE u.email ILIKE :query OR u.name ILIKE :query"
            params["query"] = f"%{query}%"
        with self.engine.connect() as conn:
            total = conn.execute(text(f"SELECT count(*) FROM users u {where}"), params).scalar_one()
            rows = conn.execute(
                text(
                    "SELECT u.id, u.email, u.name, u.role, u.email_verified, u.created_at, "
                    "(SELECT count(*) FROM aggregated_listings l WHERE l.posted_by = u.id) AS listing_count, "
                    "(SELECT count(*) FROM reports r WHERE r.reporter_id = u.id) AS report_count "
                    f"FROM users u {where} ORDER BY u.created_at DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            ).mappings().all()
        return int(total), [AdminUserItem(**dict(row)) for row in rows]
