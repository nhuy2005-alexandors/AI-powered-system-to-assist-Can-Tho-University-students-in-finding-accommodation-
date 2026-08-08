"""Geocode đa tầng (T2): địa chỉ → (lat, lng, confidence).

Tránh phí Google (P1) — dùng Nominatim/OSM. Usage policy: ≤1 req/s, User-Agent định danh.
Tầng:
  1. full address stripped admin prefix → high (số nhà)
  1b. tên đường + quận + Cần Thơ → high nếu OSM type là đường, else medium
  2. Nominatim ward+district+city → medium (tọa độ phường thật)
  3. landmark table → medium
  3b. address trần + ", Cần Thơ" (chỉ khi có ≥2 token tên riêng + type đường) → medium
  4. ward centroid hardcode → low
  5. centroid TP Cần Thơ → city
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

# centroid TP Cần Thơ (Ninh Kiều) — fallback cuối khi address không parse được nhưng
# tin chắc chắn ở CT (mọi nguồn lọc list_url theo Cần Thơ). Confidence = 'city'.
CANTHO_CENTROID = (10.0333, 105.7880)

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
    # KHÔNG đặt key "can tho" ở đây: MỌI address thật đều chứa tên thành phố, nên
    # "hẻm 9, Cần Thơ" cũng khớp → tầng 4 trả đúng CANTHO_CENTROID nhưng dán nhãn
    # 'low', tầng 5 thành code chết và 'city' gần như không bao giờ xuất hiện.
    # Biên từ KHÔNG cứu được ca này (tên thành phố là token riêng, luôn khớp biên).
    # Tâm thành phố là việc của tầng 5 (confidence 'city', không cộng quality_score).
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
    # KDC / địa danh dân gian hay gặp ở nguồn địa phương (vd nhadatcantho247) mà
    # Nominatim không có — bắt bằng bảng để tin không rơi vào 'failed' (mất khỏi map).
    "hong loan": (10.0247, 105.7573),      # KDC Hồng Loan, Cái Răng
    "91b": (10.0198, 105.7469),            # KDC 91B, Ninh Kiều/An Khánh
    "nam long": (10.0225, 105.7620),       # KDC Nam Long, Hưng Thạnh
    "hong phat": (10.0230, 105.7590),      # KDC Nam Long Hồng Phát
    # Key phải ĐỦ DÀI để không bắt bừa. Biên từ KHÔNG cứu được key số trần: "586" vẫn
    # khớp "586/12 Nguyễn Văn Cừ" (dấu "/" là biên từ) → pin sai về Cái Răng.
    # Giữ dạng có tiền tố ("kdc 586", "cho 586"), bỏ key số trần.
    "cho 586": (10.0180, 105.7500),        # KDC 586 / chợ 586, Cái Răng
    "kdc 586": (10.0180, 105.7500),
    "cty 8": (10.0090, 105.7420),          # KDC Công ty 8 (Metro), Cái Răng
    "cong ty 8": (10.0090, 105.7420),
    "phu an": (10.0210, 105.7640),         # KDC Phú An, Cái Răng
    "ecopark": (10.0160, 105.7440),        # KDC Ecopark Cần Thơ
    # "metro" trần khớp cả "metro house", "metropolitan", tên toà nhà bất kỳ → dùng
    # dạng có định danh siêu thị thật.
    "sieu thi metro": (10.0100, 105.7430),  # gần Metro/MM Mega, Cái Răng
    "mm mega": (10.0100, 105.7430),
    "vo van kiet": (10.0350, 105.7350),    # đại lộ Võ Văn Kiệt
    "nguyen van cu": (10.0230, 105.7580),  # Nguyễn Văn Cừ (trục chính SV)
    "3 thang 2": (10.0301, 105.7681),      # đường 3/2 (cạnh CTU khu II)
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


# OSM type = đường thật (tầng 1b): match rơi đúng con đường → high. Type khác
# (POI trên/gần đường như hospital/government) vẫn in-bbox → medium, không dám high.
_STREET_TYPES = frozenset({
    "primary", "secondary", "tertiary", "residential", "trunk",
    "road", "unclassified", "living_street", "pedestrian", "service",
})

# OSM type = điểm địa chỉ/toà nhà thật (tầng 1): match rơi đúng số nhà → high.
_ADDRESS_TYPES = frozenset({
    "house", "houses", "building", "yes", "apartments", "detached",
    "semidetached_house", "terrace", "bungalow", "dormitory",
})

# OSM type = đơn vị hành chính / khu dân cư (tầng 2): match rơi đúng cấp phường.
# 'residential' ở đây là place=residential (khu dân cư), không phải highway=residential.
_ADMIN_TYPES = frozenset({
    "administrative", "suburb", "quarter", "neighbourhood", "village",
    "town", "city", "hamlet", "municipality", "borough", "city_block",
    "residential", "locality", "isolated_dwelling",
})


def street_district_city(address: str) -> str | None:
    """Trích 'Đường Trần Phú, ..., Quận Y, Cần Thơ' → 'Trần Phú, Y, Cần Thơ'.

    Khác ward_district_city: GIỮ tên đường (bỏ số nhà + prefix 'Đường') để Nominatim
    pin về ĐÚNG con đường thay vì tâm phường. Trả None nếu không có phần 'Đường'.
    """
    street: str | None = None
    admin: list[str] = []
    for part in (p.strip() for p in address.split(",")):
        low = part.lower()
        if street is None and ("đường" in low or "duong" in low):
            # bỏ mọi thứ tới hết token 'Đường' (số nhà + 'hẻm ..' đứng trước) → còn tên đường
            m = re.search(r"(?:đường|duong)\s+(.+)", part, re.IGNORECASE)
            if m:
                street = m.group(1).strip()
        elif part.startswith(("Phường ", "Quận ", "Huyện ", "Xã ")):
            # GIỮ cả Phường: đường dài (Nguyễn Văn Cừ ~8km) xuyên nhiều phường,
            # bỏ phường thì Nominatim pin điểm bất kỳ trên đường → lệch vài km.
            admin.append(part.split(" ", 1)[1].strip())
        elif "Cần Thơ" in part or "Can Tho" in part:
            admin.append(part)
    if not street:
        return None
    return ", ".join([street, *admin]) if admin else street


# Token không phải tên riêng — dùng để đếm "address có tên đường thật hay không" (tầng 3b).
_FILLER_TOKENS = frozenset({
    "hem", "kdc", "duong", "so", "nhanh", "khu", "dan", "cu", "gan", "sau",
    "lung", "truc", "chinh", "doi", "dien", "canh", "ngay", "tai", "cach", "b",
})


def bare_street_in_cantho(address: str) -> str | None:
    """Address trần (không phần hành chính, không 'Cần Thơ') → '<address>, Cần Thơ'.

    Nominatim không biết address thuộc tỉnh nào nên match tên đường trùng ra HN/HCM
    rồi bị bbox chặn — 'Lý tự trọng' trả (10.7786, 106.7016) = TP.HCM. Chỉ cần thêm
    ', Cần Thơ' là nó pin đúng đường trong CT (10.0330, 105.7813). Đo 2026-08-08:
    82 tin `failed` KHÔNG phải do "string nguồn cụt" mà do thiếu token thành phố.

    Trả None nếu address không phải dạng trần, hoặc không có ≥2 token chữ thật.
    Guard token là bắt buộc: 'Hẻm 359' / 'Hẻm 105' / 'Hẻm 118-120' / 'Hẻm 3-4' không
    có tên riêng nào để match nên Nominatim trả một con đường residential bất kỳ —
    4 address khác nhau cùng ra (10.0752, 105.7287). Toạ độ sai tự tin tệ hơn 'city'
    (ADR-011: không dán nhãn lạc quan lên vị trí không biết).
    """
    norm = _norm(address)
    if "can tho" in norm:
        return None  # tầng 1 đã query kèm thành phố, không phải dạng trần
    if ward_district_city(address):
        return None  # có phần hành chính → tầng 2 lo
    words = [t for t in re.findall(r"[a-z]+", norm) if len(t) >= 2 and t not in _FILLER_TOKENS]
    if len(words) < 2:
        return None
    return f"{strip_admin(address)}, Cần Thơ"


def _match_table(
    address: str,
    table: dict[str, tuple[float, float]],
    prefer: str = "order",
) -> tuple[float, float] | None:
    """Dò key của bảng tra trong address. Match theo BIÊN TỪ, không phải substring trần.

    Substring trần bắt bừa (đo 2026-08-08 trên address thật của chotot):
      - "an hoa" khớp trong "Khu Dân Cư Văn **Hóa** Tây Đô" → pin sai 6.5km
      - "an cu"  khớp trong "Khu Dân **Cư** ..." cùng address
    `_norm` bỏ dấu nên "Hóa"→"hoa", "Cư"→"cu"; chỉ biên từ mới phân biệt được.

    prefer:
      - "order" (mặc định): key khai báo trước thắng. LANDMARKS dựa vào thứ tự này —
        "bun xang" cố ý đứng TRƯỚC "dai hoc can tho" để tin "gần ĐH Cần Thơ, hẻm bún
        xáng" snap về hồ Bún Xáng (ổ trọ SV thật) thay vì tâm Trường Nông Nghiệp.
      - "earliest": key xuất hiện SỚM NHẤT trong address thắng. Địa chỉ VN viết từ
        nhỏ đến lớn nên key sớm hơn = cấp hành chính nhỏ hơn = cụ thể hơn. Cần cho
        WARD_CENTROIDS vì bảng trộn cả phường lẫn quận: "Võ Tánh, Lê Bình, Cái Răng"
        từng trả tâm QUẬN Cái Răng chỉ vì "cai rang" khai báo trước "le binh" (lệch
        2.7km so với tâm phường Lê Bình — mất luôn thông tin phường mà address có).
    """
    norm = _norm(address)
    best: tuple[int, tuple[float, float]] | None = None
    for key, coord in table.items():
        m = re.search(rf"\b{re.escape(key)}\b", norm)
        if not m:
            continue
        if prefer != "earliest":
            return coord
        if best is None or m.start() < best[0]:
            best = (m.start(), coord)
    return best[1] if best else None


async def _nominatim(client: httpx.AsyncClient, query: str) -> tuple[float, float, str] | None:
    resp = await client.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1, "countrycodes": "vn"},
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    data = resp.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("type", "")
    return None


class Geocoder:
    """Geocode đa tầng + cache theo address (tránh gọi trùng)."""

    def __init__(self):
        self._cache: dict[str, tuple[float | None, float | None, str]] = {}
        self._client = httpx.AsyncClient(timeout=15.0)
        self._lock = asyncio.Lock()
        # True nếu lần geocode() vừa rồi có ÍT NHẤT 1 query Nominatim chết vì mạng.
        # Cần cho backfill: "Nominatim không tìm thấy" và "Nominatim không trả lời" đều
        # làm _query trả None → cùng rơi xuống bảng tra/tầng 5, nhưng hậu quả trái ngược.
        # Không có cờ này thì một lúc mạng lag sẽ hạ hàng loạt tin `high` xuống `low`
        # và người đọc DB không có cách nào biết nhãn đó là thật hay là do timeout.
        self.degraded = False

    async def __aenter__(self) -> "Geocoder":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    async def geocode(self, address: str | None) -> tuple[float | None, float | None, str]:
        self.degraded = False
        if not address or not address.strip():
            return None, None, "failed"
        if address in self._cache:
            return self._cache[address]

        result = await self._resolve(address)
        # KHÔNG cache kết quả bị lỗi mạng: cache lại thì cả run sau đó dùng chung một
        # kết quả tồi, và retry mất tác dụng.
        if not self.degraded:
            self._cache[address] = result
        return result

    async def _query(self, q: str) -> tuple[float, float, str] | None:
        """1 lần gọi Nominatim có rate-limit + nuốt lỗi mạng. Trả (lat, lng, osm_type)."""
        try:
            async with self._lock:
                await asyncio.sleep(RATE_LIMIT)
                return await _nominatim(self._client, q)
        except (httpx.HTTPError, KeyError, ValueError):
            self.degraded = True
            return None

    async def _resolve(self, address: str) -> tuple[float | None, float | None, str]:
        # Nguyên tắc chung của các tầng Nominatim: MỘT TẦNG CHỈ NHẬN KẾT QUẢ KHI OSM
        # `type` khớp thứ nó hỏi. Không khớp = Nominatim bám một POI trùng chữ, không
        # phải thứ mình tìm → giữ làm ứng viên cuối (`poi`), đi tiếp xuống bảng tra.
        # Đo 2026-08-08 khi chưa có guard này: "Khu Dân Cư Văn Hóa Tây Đô, Hưng Thạnh,
        # Cái Răng, Cần Thơ" trả type=place_of_worship (10.0047, 105.7503) và được phong
        # `high`; hai address KDC khác cùng phường cũng rơi về đúng điểm đó qua tầng 2 —
        # 3 address khác nhau, 1 toạ độ, lệch ~3km, nhãn thì `high`/`medium`.
        poi: tuple[float, float] | None = None

        # Tầng 1: full address đã strip prefix → số nhà chính xác (high)
        stripped = strip_admin(address)
        if stripped:
            r = await self._query(stripped)
            if r and _in_cantho(r[0], r[1]):
                if r[2] in _ADDRESS_TYPES or r[2] in _STREET_TYPES:
                    return r[0], r[1], "high"
                poi = (r[0], r[1])

        # Tầng 1b: tên đường + quận + Cần Thơ → pin đúng con đường thay vì tâm phường.
        # street-type = high (đúng đường); type khác nhưng in-bbox = medium (vẫn hơn
        # centroid, nhưng KHÔNG khẳng định high vì Nominatim match POI trên/gần đường).
        sdc = street_district_city(address)
        if sdc:
            r = await self._query(sdc)
            if r and _in_cantho(r[0], r[1]):
                return r[0], r[1], "high" if r[2] in _STREET_TYPES else "medium"

        # Tầng 2: Nominatim cấp phường (ward+district+city) → tọa độ phường thật (medium).
        # Guard type hành chính: query cấp phường mà OSM trả POI nghĩa là nó KHÔNG có
        # ranh giới phường khớp tên, chỉ vơ một điểm trùng chữ trong vùng — nhận nó làm
        # "tâm phường" là sai cả toạ độ (lệch tới 3km) lẫn nhãn. Rơi xuống bảng tra tay
        # (tầng 4) trung thực hơn: đúng cấp phường, nhãn `low`.
        wdc = ward_district_city(address)
        if wdc:
            r = await self._query(wdc)
            if r and _in_cantho(r[0], r[1]):
                if r[2] in _ADMIN_TYPES:
                    return r[0], r[1], "medium"
                poi = poi or (r[0], r[1])

        # Tầng 3: landmark table (medium)
        lm = _match_table(address, LANDMARKS)
        if lm:
            return lm[0], lm[1], "medium"

        # Tầng 3b: address trần + ", Cần Thơ" → cứu tin không có phần hành chính.
        # Xếp SAU landmark (toạ độ tay đã verify thắng phỏng đoán của Nominatim) và
        # CHỈ nhận khi OSM type là đường thật: type khác (hotel/clothes/bicycle_rental)
        # nghĩa là Nominatim bám 1 POI trùng chữ, không phải con đường trong address.
        # Confidence 'medium' chứ không 'high' — không có số nhà, chỉ biết đúng đường.
        bsc = bare_street_in_cantho(address)
        if bsc:
            r = await self._query(bsc)
            if r and _in_cantho(r[0], r[1]) and r[2] in _STREET_TYPES:
                return r[0], r[1], "medium"

        # Tầng 4: ward centroid hardcode (low). prefer="earliest": bảng trộn cả phường
        # lẫn quận, địa chỉ VN viết nhỏ→lớn nên key xuất hiện sớm hơn là cấp cụ thể hơn.
        wc = _match_table(address, WARD_CENTROIDS, prefer="earliest")
        if wc:
            return wc[0], wc[1], "low"

        # Tầng 4b: POI trùng chữ mà tầng 1/2 đã từ chối. Xếp DƯỚI bảng tra tay vì tâm
        # phường hardcode chắc chắn đúng cấp phường, còn POI chỉ chắc "ở đâu đó trong
        # Cần Thơ" (đo được lệch tới 3km). Vẫn hơn tâm TP vì có liên quan tới address.
        # Nhãn `low`: quality_score chỉ cộng 0.20 cho high/medium (cleaner/pipeline.py:123)
        # nên toạ độ chưa xác thực này không tự nâng điểm chất lượng của tin.
        if poi:
            return poi[0], poi[1], "low"

        # Tầng 5: centroid TP Cần Thơ (confidence 'city'). Mọi nguồn đều lọc list_url
        # theo Cần Thơ → address không parse được (vd "CTY 8", "hẻm 9") vẫn CHẮC ở CT.
        # Toạ độ tâm TP còn hơn 'failed' (mất khỏi bản đồ/nearby). Downstream lọc theo
        # confidence nếu muốn loại 'city' khỏi thống kê chính xác.
        return CANTHO_CENTROID[0], CANTHO_CENTROID[1], "city"


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Khoảng cách mét giữa 2 tọa độ (tham khảo; production dùng PostGIS ST_Distance)."""
    import math

    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(r * 2 * math.asin(math.sqrt(a)), 1)
