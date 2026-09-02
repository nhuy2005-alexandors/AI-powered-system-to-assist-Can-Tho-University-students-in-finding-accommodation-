"""Geocode đa tầng (T2): địa chỉ → (lat, lng, confidence).

Tránh phí Google (P1) — dùng Nominatim/OSM. Usage policy: ≤1 req/s, User-Agent định danh.
Tầng:
  1. full address stripped admin prefix → high (số nhà)
  2. Nominatim ward+district+city → medium (tọa độ phường thật)
  3. landmark table → medium
  4. ward centroid hardcode → low
  5. failed
Nominatim KHÔNG hiểu prefix "Phường/Quận/Đường" → phải strip trước khi query.
"""
import asyncio
import re
import unicodedata

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# User-Agent định danh theo Nominatim usage policy
USER_AGENT = "TroCTU-NCKH/1.0 (contact: phub2303891@student.ctu.edu.vn)"
RATE_LIMIT = 1.0  # giây/req

# tọa độ CTU khu 2 (cổng chính, đường 3/2) — hằng số tính distance_to_ctu
CTU_LAT, CTU_LNG = 10.0301, 105.7681

# prefix hành chính Nominatim không parse được → strip
_ADMIN_PREFIXES = ("Phường ", "Quận ", "Xã ", "Thị trấn ", "Huyện ", "khu vực ", "Khu vực ")

# centroid phường/quận quanh CTU (low confidence fallback cuối)
WARD_CENTROIDS: dict[str, tuple[float, float]] = {
    "ninh kieu": (10.0333, 105.7880),
    "xuan khanh": (10.0290, 105.7700),
    "an khanh": (10.0345, 105.7600),
    "an hoa": (10.0540, 105.7790),
    "an cu": (10.0360, 105.7820),
    "an nghiep": (10.0310, 105.7770),
    "an phu": (10.0380, 105.7850),
    "an binh": (10.0250, 105.7580),
    "hung loi": (10.0230, 105.7720),
    "cai rang": (10.0150, 105.7700),
    "le binh": (10.0100, 105.7770),
    "phu thu": (9.9728, 105.7404),
    "ba lang": (9.9950, 105.7550),
    "binh thuy": (10.0640, 105.7330),
    "an thoi": (10.0617, 105.7654),
    "tra noc": (10.0870, 105.7080),
    "long tuyen": (10.0480, 105.7200),
    "tan an": (10.0420, 105.7920),
    "thoi an dong": (10.0050, 105.7350),
    "phong dien": (10.0800, 105.6700),
    "o mon": (10.1100, 105.6250),
    "can tho": (10.0333, 105.7880),  # fallback cấp thành phố
}

# landmark phổ biến SV hay nhắc
LANDMARKS: dict[str, tuple[float, float]] = {
    # Hồ Bún Xáng — ổ trọ SV rìa campus khu II. PHẢI đứng TRƯỚC "dai hoc can tho":
    # tin "gần ĐH Cần Thơ" mà có "bún xáng" thì snap về hồ, không về giữa trường.
    "bun xang": (10.0318, 105.7641),
    "dai hoc can tho": (CTU_LAT, CTU_LNG),
    "ctu": (CTU_LAT, CTU_LNG),
    "dai hoc y duoc": (10.0270, 105.7690),
    "dai hoc nam can tho": (10.0100, 105.7450),
    "dai hoc fpt": (10.0120, 105.7480),
    "xuan khanh": (10.0290, 105.7700),
    "vincom": (10.0316, 105.7745),
    "sen hong": (10.0330, 105.7830),
    "ben xe": (10.0490, 105.7820),
    "san bay": (10.0850, 105.7120),
    "cho can tho": (10.0350, 105.7900),
}


# bbox Cần Thơ (lat, lng) — chặn Nominatim match tên đường trùng ra tỉnh khác (HN/HCM).
# Rộng đủ ôm mọi ward centroid quanh CTU, hẹp đủ loại 21.x (HN) / 10.75,106.6 (HCM).
_CT_LAT = (9.8, 10.3)
_CT_LNG = (105.4, 106.0)


def _in_cantho(lat: float, lng: float) -> bool:
    return _CT_LAT[0] <= lat <= _CT_LAT[1] and _CT_LNG[0] <= lng <= _CT_LNG[1]


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.replace("đ", "d")  # Đ/đ không phải dấu tổ hợp, xử lý riêng


def strip_admin(address: str) -> str:
    """Bỏ prefix hành chính + 'Đường' để Nominatim parse được số nhà/tên đường."""
    a = address
    for p in (*_ADMIN_PREFIXES, "Đường ", "đường "):
        a = a.replace(p, "")
    return re.sub(r"\s+", " ", a).strip(" ,")


def ward_district_city(address: str) -> str | None:
    """Tách 'Phường X, Quận Y, Cần Thơ' → 'X, Y, Cần Thơ' (Nominatim match cấp phường).

    Trả None nếu không tách được phần hành chính nào.
    """
    # chỉ cấp hành chính chính thức (không gồm "khu vực" — đó là địa danh phụ)
    admin_prefixes = ("Phường ", "Quận ", "Xã ", "Thị trấn ", "Huyện ")
    admin: list[str] = []
    for part in (p.strip() for p in address.split(",")):
        matched = False
        for pre in admin_prefixes:
            if part.startswith(pre):
                admin.append(part[len(pre):].strip())
                matched = True
                break
        if not matched and ("Cần Thơ" in part or "Can Tho" in part):
            admin.append(part)
    return ", ".join(admin) if admin else None


def _match_table(address: str, table: dict[str, tuple[float, float]]) -> tuple[float, float] | None:
    norm = _norm(address)
    for key, coord in table.items():
        if key in norm:
            return coord
    return None


async def _nominatim(client: httpx.AsyncClient, query: str) -> tuple[float, float] | None:
    resp = await client.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1, "countrycodes": "vn"},
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    data = resp.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None


class Geocoder:
    """Geocode đa tầng + cache theo address (tránh gọi trùng)."""

    def __init__(self):
        self._cache: dict[str, tuple[float | None, float | None, str]] = {}
        self._client = httpx.AsyncClient(timeout=15.0)
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "Geocoder":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    async def geocode(self, address: str | None) -> tuple[float | None, float | None, str]:
        if not address or not address.strip():
            return None, None, "failed"
        if address in self._cache:
            return self._cache[address]

        result = await self._resolve(address)
        self._cache[address] = result
        return result

    async def _query(self, q: str) -> tuple[float, float] | None:
        """1 lần gọi Nominatim có rate-limit + nuốt lỗi mạng."""
        try:
            async with self._lock:
                await asyncio.sleep(RATE_LIMIT)
                return await _nominatim(self._client, q)
        except (httpx.HTTPError, KeyError, ValueError):
            return None

    async def _resolve(self, address: str) -> tuple[float | None, float | None, str]:
        # Tầng 1: full address đã strip prefix → số nhà chính xác (high)
        stripped = strip_admin(address)
        if stripped:
            coord = await self._query(stripped)
            if coord and _in_cantho(*coord):
                return coord[0], coord[1], "high"

        # Tầng 2: Nominatim cấp phường (ward+district+city) → tọa độ phường thật (medium)
        wdc = ward_district_city(address)
        if wdc:
            coord = await self._query(wdc)
            if coord and _in_cantho(*coord):
                return coord[0], coord[1], "medium"

        # Tầng 3: landmark table (medium)
        lm = _match_table(address, LANDMARKS)
        if lm:
            return lm[0], lm[1], "medium"

        # Tầng 4: ward centroid hardcode (low)
        wc = _match_table(address, WARD_CENTROIDS)
        if wc:
            return wc[0], wc[1], "low"

        return None, None, "failed"


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Khoảng cách mét giữa 2 tọa độ (tham khảo; production dùng PostGIS ST_Distance)."""
    import math

    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(r * 2 * math.asin(math.sqrt(a)), 1)
