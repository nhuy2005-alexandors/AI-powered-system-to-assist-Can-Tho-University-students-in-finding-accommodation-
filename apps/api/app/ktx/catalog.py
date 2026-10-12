from __future__ import annotations

import re
import unicodedata
from typing import Literal
from datetime import date
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator, ConfigDict


class KtxRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


def fold_text(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower()).replace("đ", "d")
    return re.sub(r"\s+", " ", "".join(c for c in value if unicodedata.category(c) != "Mn")).strip()


class KtxSource(KtxRecord):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length=1, max_length=200)
    url: str | None = None
    year: int | None = None
    note: str = Field(max_length=4000)


class KtxLocation(KtxRecord):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    source_url: str
    source_name: str
    osm_type: str
    osm_id: int
    precision: Literal["representative"]
    verified_at: str
    label: str


class KtxDormitory(KtxRecord):
    id: Literal["A", "B"]
    name: str = Field(min_length=1, max_length=200)
    capacity: int = Field(ge=0, le=100000)
    description: str = Field(max_length=4000)
    buildings: str
    phone: str
    cover: str
    location: KtxLocation


class KtxRoomType(KtxRecord):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    code: str = Field(min_length=1, max_length=40)
    area_ids: list[Literal["A", "B"]]
    capacities: list[int] = Field(min_length=1, max_length=16)
    capacity_label: str = Field(min_length=1, max_length=100)
    cooking_allowed: bool | None
    bed_type: Literal["single", "bunk", "unknown"]
    bathroom: str | None = None
    description: str = Field(max_length=4000)
    price: int = Field(gt=0, le=1000000000)
    price_period: Literal["unconfirmed", "monthly", "semester_3_5_months"]
    source_id: str
    notes: str = Field(max_length=4000)


class KtxFact(KtxRecord):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    source_id: str
    tags: list[str] = Field(max_length=30)


class KtxPhysicalRoom(KtxRecord):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    dormitory_id: Literal["A", "B"]
    building: str = Field(min_length=1, max_length=80)
    number: str = Field(min_length=1, max_length=40)
    room_type_id: str
    capacity: int = Field(ge=1, le=100)
    status: Literal["unknown", "available", "full", "maintenance"] = "unknown"
    available_beds: int | None = Field(default=None, ge=0)
    verified_at: date | None = None
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def occupancy(self):
        if self.available_beds is not None and self.available_beds > self.capacity:
            raise ValueError("Số chỗ trống vượt sức chứa")
        if self.status != "unknown" or self.available_beds is not None:
            if self.verified_at is None or self.verified_at > date.today():
                raise ValueError("Cần ngày ghi nhận hợp lệ, không nằm trong tương lai")
        if self.status == "available" and not self.available_beds:
            raise ValueError("Phòng còn chỗ phải có số chỗ trống lớn hơn 0")
        if self.status in {"full", "maintenance"} and self.available_beds not in (None, 0):
            raise ValueError("Phòng hết chỗ/bảo trì không có chỗ trống")
        return self


class KtxImage(KtxRecord):
    src: str
    alt: str = Field(min_length=1, max_length=500)
    dormitory_id: Literal["A", "B"]
    original_url: str
    source_url: str
    credit: str
    sha256: str
    bytes: int
    room_id: str | None = None
    room_type_id: str | None = None


class KtxCatalog(KtxRecord):
    version: str
    academic_year: str | None = Field(default=None, pattern=r"^20\d{2}-20\d{2}$")
    term: str = Field(default="", max_length=100)
    updated_at: str
    email: str
    address: str
    registration_url: str
    sources: list[KtxSource] = Field(min_length=1, max_length=100)
    dormitories: list[KtxDormitory] = Field(min_length=2, max_length=2)
    room_types: list[KtxRoomType] = Field(max_length=500)
    rooms: list[KtxPhysicalRoom] = Field(default_factory=list, max_length=5000)
    facts: list[KtxFact] = Field(max_length=200)
    images: list[KtxImage] = Field(max_length=300)

    @model_validator(mode="after")
    def references(self):
        sources = {s.id for s in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("Duplicate source IDs")
        fact_ids = [fact.id for fact in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("Trùng mã thông tin tư vấn")
        ids = [room.id for room in self.room_types]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate room type IDs")
        for record in [*self.room_types, *self.facts]:
            if record.source_id not in sources:
                raise ValueError("Unknown source ID: " + record.source_id)
        if {area.id for area in self.dormitories} != {"A", "B"}:
            raise ValueError("The catalogue must contain areas A and B")
        if self.academic_year:
            start, end = map(int, self.academic_year.split("-"))
            if end != start + 1:
                raise ValueError("Năm học phải gồm hai năm liên tiếp")
        for room in self.room_types:
            if any(n < 1 or n > 100 for n in room.capacities):
                raise ValueError("Sức chứa loại phòng phải trong khoảng 1–100")
        room_ids = {room.id for room in self.rooms}
        if len(room_ids) != len(self.rooms):
            raise ValueError("Trùng mã phòng")
        positions = {(room.dormitory_id, room.building.strip().casefold(), room.number.strip().casefold()) for room in self.rooms}
        if len(positions) != len(self.rooms):
            raise ValueError("Trùng số phòng trong cùng khu và dãy")
        for room in self.rooms:
            if room.room_type_id not in ids:
                raise ValueError("Phòng tham chiếu loại phòng không tồn tại")
            room_type = next(r for r in self.room_types if r.id == room.room_type_id)
            if room_type.area_ids and room.dormitory_id not in room_type.area_ids:
                raise ValueError("Khu của phòng không khớp loại phòng")
            if room.capacity not in room_type.capacities:
                raise ValueError("Sức chứa phòng không khớp loại phòng")
        for image in self.images:
            if image.room_id and image.room_id not in room_ids:
                raise ValueError("Ảnh tham chiếu phòng không tồn tại")
            if image.room_type_id and image.room_type_id not in ids:
                raise ValueError("Ảnh tham chiếu loại phòng không tồn tại")
            if image.room_id:
                linked = next(r for r in self.rooms if r.id == image.room_id)
                if linked.dormitory_id != image.dormitory_id:
                    raise ValueError("Khu của ảnh không khớp phòng")
                if image.room_type_id and linked.room_type_id != image.room_type_id:
                    raise ValueError("Loại phòng của ảnh không khớp phòng")
        def public_url(value):
            if not value:
                return
            url = urlparse(value)
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
                raise ValueError("Liên kết phải là URL http/https công khai")
        def local_image(value):
            if not re.fullmatch(r"/images/ktx/[a-zA-Z0-9_.-]+|/api/ktx/images/[a-f0-9-]{36}", value):
                raise ValueError("Chỉ dùng ảnh có sẵn trong thư viện hoặc ảnh tải lên hệ thống")
        for source in self.sources:
            public_url(source.url)
        public_url(self.registration_url)
        for area in self.dormitories:
            local_image(area.cover)
            public_url(area.location.source_url)
        if len({image.src for image in self.images}) != len(self.images):
            raise ValueError("Trùng ảnh trong danh mục")
        for image in self.images:
            local_image(image.src)
            public_url(image.source_url)
            public_url(image.original_url)
        return self


def room_text(room: KtxRoomType, academic_year: str | None = None) -> str:
    area = ", ".join("khu " + a for a in room.area_ids) or "khu chưa xác nhận"
    year = f" ({academic_year.split('-')[0]})" if academic_year else ""
    unit = ("đồng/người/tháng" if room.price_period == "monthly" else
            "đồng/người/học kỳ 3,5 tháng" + year if room.price_period == "semester_3_5_months" else
            "đồng/người · chưa xác nhận kỳ tính giá")
    price = f"{room.price:,}".replace(",", ".")
    details = []
    if room.cooking_allowed is not None:
        details.append("được nấu ăn" if room.cooking_allowed else "không được nấu ăn")
    if room.bed_type != "unknown":
        details.append("giường tầng" if room.bed_type == "bunk" else "giường bộ")
    if room.bathroom:
        details.append("vệ sinh: " + room.bathroom)
    amenities = "; ".join(details)
    return f"KTX CTU · {room.code} · {area} · sức chứa {room.capacity_label}. {room.description}. {amenities}. Giá {price} {unit}. {room.notes}"
