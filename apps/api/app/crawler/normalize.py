import hashlib
import re
import unicodedata

from .schemas import NormalizedListing, RawListing

# từ khóa tiện ích → key chuẩn
AMENITY_KEYWORDS = {
    "wifi": ["wifi", "internet"],
    "air_conditioner": ["máy lạnh", "điều hòa", "may lanh", "dieu hoa"],
    "private_wc": ["wc riêng", "vệ sinh riêng", "toilet riêng"],
    "parking": ["để xe", "gửi xe", "bãi xe", "chỗ để xe"],
    "kitchen": ["bếp", "nấu ăn", "kitchen"],
    "fridge": ["tủ lạnh"],
    "washing_machine": ["máy giặt"],
    "free_hours": ["giờ giấc tự do", "tự do giờ giấc"],
}

_NUM_RE = re.compile(r"[\d.,]+")


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def parse_price(text: str | None) -> int | None:
    """'2,5 triệu/tháng' -> 2500000 ; '1.8 triệu' -> 1800000 ; '800 nghìn' -> 800000 ; '3.000.000' -> 3000000."""
    if not text:
        return None
    low = _strip_accents(text.lower())
    has_unit = any(u in low for u in ("trieu", "tr", "nghin", "ngan", "k"))
    m = _NUM_RE.search(low.replace(" ", ""))
    if not m:
        return None
    token = m.group(0)
    if has_unit:
        # đơn vị triệu/nghìn → chỉ có 1 dấu thập phân ('.' hoặc ',')
        num = float(token.replace(",", "."))
    else:
        # số trần → '.'/',' là dấu phân nhóm nghìn
        num = float(token.replace(".", "").replace(",", ""))
    if "trieu" in low or "tr" in low:
        return int(num * 1_000_000)
    if "nghin" in low or "ngan" in low or "k" in low:
        return int(num * 1_000)
    return int(num)


def parse_area(text: str | None) -> float | None:
    """'25 m2' -> 25.0 ; '30m²' -> 30.0."""
    if not text:
        return None
    m = _NUM_RE.search(text.replace(" ", ""))
    if not m:
        return None
    return float(m.group(0).replace(",", "."))


def parse_amenities(*texts: str | None) -> dict[str, bool]:
    blob = _strip_accents(" ".join(t for t in texts if t).lower())
    result: dict[str, bool] = {}
    for key, kws in AMENITY_KEYWORDS.items():
        result[key] = any(_strip_accents(kw.lower()) in blob for kw in kws)
    return result


def compute_content_hash(n: "NormalizedListing") -> str:
    """Hash ổn định trên field nội dung — đổi giá/diện tích/mô tả → đổi hash → trigger update."""
    parts = [
        n.title.strip().lower(),
        str(n.price or ""),
        str(n.area or ""),
        (n.address or "").strip().lower(),
        (n.description or "").strip().lower(),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def normalize(raw: RawListing) -> NormalizedListing:
    n = NormalizedListing(
        source=raw.source,
        source_id=raw.source_id,
        source_url=raw.source_url,
        title=raw.title.strip(),
        price=parse_price(raw.price_text),
        area=parse_area(raw.area_text),
        address=(raw.address or "").strip() or None,
        district=raw.district,
        description=(raw.description or "").strip() or None,
        images=raw.images,
        amenities=parse_amenities(raw.amenities_text, raw.description, raw.title),
    )
    n.content_hash = compute_content_hash(n)
    return n
