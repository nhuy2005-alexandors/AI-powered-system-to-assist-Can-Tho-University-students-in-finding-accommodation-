import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.crawler.normalize import extract_area_from_text, _strip_accents

log = logging.getLogger("cleaner.pipeline")

# ── Labels dùng khi generate title placeholder ──
_TYPE_LABELS = {
    "phong_tro": "Phòng trọ",
    "nha_nguyen_can": "Nhà nguyên căn",
    "mat_bang": "Mặt bằng",
    "khac": "Chỗ ở",
}


def _impute_area_from_price(price: int | None) -> float:
    """Heuristic đoán diện tích theo mức giá khi không có area/regex."""
    if not price or price <= 0:
        return 0.0
    if price < 1_000_000:
        return 15.0
    elif price < 1_500_000:
        return 20.0
    elif price < 2_500_000:
        return 25.0
    elif price < 4_000_000:
        return 30.0
    return 40.0


# ── T1: Phân loại ──
def classify(title: str | None, price: int | None, area: float | None) -> str:
    """Phân loại listing_type từ title (bỏ dấu, lowercase) + giá/diện tích fallback."""
    blob = _strip_accents((title or "").lower())

    if any(kw in blob for kw in ("mat bang", "kho", "xuong", "van phong", "kinh doanh")):
        return "mat_bang"

    if any(
        kw in blob
        for kw in ("phong tro", "nha tro", "phong cho thue", "ky tuc", "o ghep", "phong ")
    ):
        return "phong_tro"

    if any(kw in blob for kw in ("nha nguyen can", "nha mat tien", "nguyen can", "biet thu")):
        return "nha_nguyen_can"
    if price is not None and price > 6_000_000 and area is not None and area > 60:
        return "nha_nguyen_can"

    if price is not None and price <= 4_000_000 and area is not None and area <= 40:
        return "phong_tro"

    return "khac"


# ── T2: Validate giá theo loại ──
def validate(listing_type: str, price: int | None) -> tuple[bool, str | None]:
    """Kiểm tra giá hợp lý theo listing_type. Trả (is_valid, reject_reason)."""
    if price is None:
        return False, "Thiếu giá"

    if listing_type == "phong_tro":
        if 300_000 <= price <= 8_000_000:
            return True, None
        return False, "Giá ngoài khoảng phòng trọ"

    if listing_type in ("nha_nguyen_can", "mat_bang"):
        if 1_000_000 <= price <= 50_000_000:
            return True, None
        return False, "Giá ngoài khoảng nhà/mặt bằng"

    # khac
    if 300_000 <= price <= 20_000_000:
        return True, None
    return False, "Giá bất thường"


# ── T3: Resolve diện tích ──
def resolve_area(
    area: float | None, price: int | None, description: str | None
) -> tuple[float, bool]:
    """Trả (area, is_imputed). Ưu tiên area có sẵn > regex mô tả > heuristic theo giá."""
    if area is not None and area > 0:
        return area, False

    extracted = extract_area_from_text(description)
    if extracted is not None:
        return extracted, False

    return _impute_area_from_price(price), True


# ── T4: Normalize title ──
def normalize_title(
    title: str | None, listing_type: str, area: float, district: str | None
) -> str:
    """Giữ title gốc nếu đủ dài (>=15 ký tự); ngược lại generate placeholder."""
    if title and len(title.strip()) >= 15:
        return title

    label = _TYPE_LABELS.get(listing_type, "Chỗ ở")
    return f"{label} {area}m² tại {district or 'Cần Thơ'}"


# ── T5: Quality score ──
def score(
    listing_type: str,
    is_imputed_area: bool,
    geocode_confidence: str | None,
    images,
    description: str | None,
    district: str | None,
) -> float:
    """Tổng điểm chất lượng, clamp [0,1], round 2 chữ số."""
    total = 0.0
    if listing_type == "phong_tro":
        total += 0.30
    if not is_imputed_area:
        total += 0.20
    if geocode_confidence in ("high", "medium"):
        total += 0.20
    if images:
        total += 0.15
    if description and len(description) >= 50:
        total += 0.10
    if district and district != "Không rõ":
        total += 0.05

    return round(max(0.0, min(1.0, total)), 2)


def run_cleaner(engine: Engine) -> None:
    """ETL pipeline 5 tầng: classify -> validate -> resolve_area -> normalize_title -> score."""
    log.info("Starting Data Cleaning Pipeline...")

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, title, price, area, description, district,
                       source_url, images, geocode_confidence
                FROM aggregated_listings
                WHERE cleaning_status = 'raw'
                """
            )
        ).mappings().all()

        if not rows:
            log.info("No raw rows to clean.")
            return

        cleaned_count = 0
        rejected_count = 0
        imputed_count = 0
        type_counts: dict[str, int] = {}

        for r in rows:
            l_id = r["id"]
            title = r["title"] or ""
            price = r["price"]
            area = r["area"]
            desc = r["description"]
            district = r["district"]
            images = r["images"]
            geocode_confidence = r["geocode_confidence"]

            logs: list[str] = []

            # 1. Classify
            lt = classify(title, price, area)

            # 2. Validate
            is_valid, reason = validate(lt, price)
            if not is_valid:
                conn.execute(
                    text(
                        """
                        UPDATE aggregated_listings
                        SET listing_type = :listing_type,
                            cleaning_status = 'rejected',
                            quality_score = 0,
                            cleaning_logs = :logs,
                            updated_at = now()
                        WHERE id = :id
                        """
                    ),
                    {"listing_type": lt, "logs": reason, "id": l_id},
                )
                rejected_count += 1
                type_counts[lt] = type_counts.get(lt, 0) + 1
                continue

            # 3. Resolve area
            resolved_area, is_imputed = resolve_area(area, price, desc)
            if is_imputed:
                logs.append(f"Area imputed: {resolved_area}")
            elif area is None or area <= 0:
                logs.append(f"Area extracted from description: {resolved_area}")

            # 4. Normalize title
            new_title = normalize_title(title, lt, resolved_area, district)
            if new_title != title:
                logs.append("Title normalized")

            # 5. Score
            q = score(lt, is_imputed, geocode_confidence, images, desc, district)

            conn.execute(
                text(
                    """
                    UPDATE aggregated_listings
                    SET title = :title,
                        area = :area,
                        listing_type = :listing_type,
                        cleaning_status = 'cleaned',
                        quality_score = :quality_score,
                        is_imputed_area = :is_imputed,
                        cleaning_logs = :logs,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {
                    "title": new_title,
                    "area": resolved_area,
                    "listing_type": lt,
                    "quality_score": q,
                    "is_imputed": is_imputed,
                    "logs": " | ".join(logs) if logs else None,
                    "id": l_id,
                },
            )

            cleaned_count += 1
            type_counts[lt] = type_counts.get(lt, 0) + 1
            if is_imputed:
                imputed_count += 1

        type_summary = ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items()))
        log.info(
            f"Cleaner finished: Processed {len(rows)}, Cleaned {cleaned_count}, "
            f"Rejected {rejected_count}, Imputed Area {imputed_count}, Types: {type_summary}"
        )
