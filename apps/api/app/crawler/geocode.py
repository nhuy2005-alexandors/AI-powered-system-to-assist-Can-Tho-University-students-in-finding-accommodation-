"""Geocode đa tầng (T2): địa chỉ → (lat, lng, confidence).

Tránh phí Google (P1) — dùng Nominatim/OSM. Usage policy: ≤1 req/s, User-Agent định danh.
Tầng: full address (high) → landmark (medium) → ward/district centroid (low) → failed.
"""
import asyncio
import unicodedata

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# User-Agent định danh theo Nominatim usage policy
USER_AGENT = "TroCTU-NCKH/1.0 (contact: phub2303891@student.ctu.edu.vn)"
RATE_LIMIT = 1.0  # giây/req

# tọa độ CTU khu 2 (cổng chính, đường 3/2) — hằng số tính distance_to_ctu
CTU_LAT, CTU_LNG = 10.0301, 105.7681

# centroid phường/quận quanh CTU (low confidence fallback)
WARD_CENTROIDS: dict[str, tuple[float, float]] = {
    "ninh kieu": (10.0333, 105.7880),
    "xuan khanh": (10.0290, 105.7700),
    "an khanh": (10.0345, 105.7600),
    "an hoa": (10.0540, 105.7790),
    "cai rang": (10.0150, 105.7700),
    "binh thuy": (10.0640, 105.7330),
    "an cu": (10.0360, 105.7820),
    "tan an": (10.0420, 105.7920),
}

# landmark phổ biến SV hay nhắc
LANDMARKS: dict[str, tuple[float, float]] = {
    "dai hoc can tho": (CTU_LAT, CTU_LNG),
    "ctu": (CTU_LAT, CTU_LNG),
    "xuan khanh": (10.0290, 105.7700),
    "vincom": (10.0316, 105.7745),
    "ben xe": (10.0490, 105.7820),
}


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.replace("đ", "d")  # Đ/đ không phải dấu tổ hợp, xử lý riêng


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

    async def _resolve(self, address: str) -> tuple[float | None, float | None, str]:
        # Tầng 1: Nominatim địa chỉ đầy đủ
        try:
            async with self._lock:
                await asyncio.sleep(RATE_LIMIT)
                coord = await _nominatim(self._client, address)
            if coord:
                return coord[0], coord[1], "high"
        except (httpx.HTTPError, KeyError, ValueError):
            pass

        # Tầng 2: landmark
        lm = _match_table(address, LANDMARKS)
        if lm:
            return lm[0], lm[1], "medium"

        # Tầng 3: ward/district centroid
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
