from __future__ import annotations

import re
from dataclasses import dataclass

from .providers import normalize_text
from .schemas import ChatFilters


DISTRICTS = {
    "ninh kieu": "Ninh Kiều",
    "cai rang": "Cái Răng",
    "binh thuy": "Bình Thủy",
    "o mon": "Ô Môn",
    "thot not": "Thốt Nốt",
    "phong dien": "Phong Điền",
    "co do": "Cờ Đỏ",
    "thoi lai": "Thới Lai",
    "vinh thanh": "Vĩnh Thạnh",
}

AMENITIES = {
    "may lanh": "air_conditioner",
    "dieu hoa": "air_conditioner",
    "wifi": "wifi",
    "internet": "wifi",
    "gac": "mezzanine",
    "gac lung": "mezzanine",
    "cho de xe": "parking",
    "giu xe": "parking",
    "wc rieng": "private_bathroom",
    "ve sinh rieng": "private_bathroom",
    "tu lanh": "refrigerator",
    "may giat": "washing_machine",
    "bep": "kitchen",
    "nuoi thu cung": "pets_allowed",
    "gio giac tu do": "flexible_hours",
}


@dataclass(frozen=True)
class ParsedQuery:
    intent: str
    filters: ChatFilters
    confidence: float


def _money(value: str, unit: str | None) -> int:
    number = float(value.replace(",", "."))
    if unit in {"tr", "trieu"}:
        return int(number * 1_000_000)
    if unit in {"k", "nghin", "ngan"}:
        return int(number * 1_000)
    return int(number)


def _prices(text: str) -> tuple[int | None, int | None]:
    pattern = r"(\d+(?:[\.,]\d+)?)\s*(trieu|tr|k|nghin|ngan|dong)?"
    between = re.search(rf"(?:tu|khoang)\s+{pattern}\s+(?:den|toi|-)\s+{pattern}", text)
    if between:
        return _money(between.group(1), between.group(2)), _money(between.group(3), between.group(4))
    max_match = re.search(rf"(?:duoi|khong qua|toi da|tam|<=)\s*{pattern}", text)
    min_match = re.search(rf"(?:tren|toi thieu|it nhat|>=)\s*{pattern}", text)
    min_price = _money(min_match.group(1), min_match.group(2)) if min_match else None
    max_price = _money(max_match.group(1), max_match.group(2)) if max_match else None
    if min_price is None and max_price is None:
        budget = re.search(r"(\d+(?:[\.,]\d+)?)\s*(trieu|tr|k|nghin|ngan)\b", text)
        if budget:
            max_price = _money(budget.group(1), budget.group(2))
    return min_price, max_price


def parse_query(message: str) -> ParsedQuery:
    text = normalize_text(message)
    housing_terms = ("phong", "tro", "nha", "thue", "cho o", "can ho", "mat bang", "ctu", "truong")
    out_terms = ("thoi tiet", "bong da", "lap trinh", "chung khoan", "nau an", "tin tuc")
    if any(term in text for term in out_terms) and not any(term in text for term in housing_terms):
        return ParsedQuery("out_of_scope", ChatFilters(), 0.98)

    min_price, max_price = _prices(text)
    district = next((label for key, label in DISTRICTS.items() if key in text), None)
    amenities = sorted({value for key, value in AMENITIES.items() if key in text})

    min_area = None
    area_match = re.search(r"(?:tren|toi thieu|it nhat)\s*(\d+(?:[\.,]\d+)?)\s*m(?:2| vuong)?", text)
    if area_match:
        min_area = float(area_match.group(1).replace(",", "."))

    max_distance = None
    distance_match = re.search(r"(?:cach(?: truong| ctu)?|trong vong|duoi|khong qua)\s*(\d+(?:[\.,]\d+)?)\s*(km|m)\b", text)
    if distance_match:
        max_distance = float(distance_match.group(1).replace(",", "."))
        if distance_match.group(2) == "km":
            max_distance *= 1000

    max_minutes = None
    minute_match = re.search(r"(?:duoi|khong qua|trong vong)\s*(\d+)\s*phut", text)
    if minute_match:
        max_minutes = float(minute_match.group(1))

    gender = None
    if "chi nu" in text or "nu thue" in text:
        gender = "female"
    elif "chi nam" in text or "nam thue" in text:
        gender = "male"

    listing_type = "phong_tro"
    if "nha nguyen can" in text:
        listing_type = "nha_nguyen_can"
    elif "mat bang" in text:
        listing_type = "mat_bang"

    filters = ChatFilters(
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        district=district,
        amenities=amenities,
        gender=gender,
        max_distance_ctu=max_distance,
        max_route_minutes=max_minutes,
        listing_type=listing_type,
    )
    evidence = sum(
        value not in (None, [], "phong_tro")
        for value in filters.model_dump().values()
    )
    intent = "find_listing" if any(term in text for term in housing_terms) or evidence else "clarify"
    return ParsedQuery(intent, filters, min(0.98, 0.72 + evidence * 0.04))


def merge_filters(parsed: ChatFilters, explicit: ChatFilters | None) -> ChatFilters:
    if explicit is None:
        return parsed
    data = parsed.model_dump()
    for key, value in explicit.model_dump(exclude_none=True).items():
        if key == "amenities":
            data[key] = sorted(set(data.get(key, [])) | set(value))
        else:
            data[key] = value
    return ChatFilters(**data)
