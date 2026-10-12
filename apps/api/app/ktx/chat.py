"""Answer KTX catalogue questions from the same records served to the website."""
from __future__ import annotations

import logging
import re
import time

from sqlalchemy.exc import SQLAlchemyError

from .catalog import fold_text, room_text
from .repo import KtxRepository
from ..room_service.chatbot.parser import _prices
from ..room_service.chatbot.schemas import ChatAskResponse, ChatSource, ChatEvaluationContext
from ..room_service.chatbot.topics import question_categories

log = logging.getLogger(__name__)


def matching_codes(catalog, query):
    normalized = fold_text(query)
    codes = []
    for room in catalog.room_types:
        code = fold_text(room.code)
        # The bare letter A in 'khu A' names an area, not room code A.
        if code == "a" and normalized != "a" and not re.search(r"\bphong\s+a\b(?!\s*\d)", normalized):
            continue
        if re.search(r"(?<!\w)" + re.escape(code) + r"(?!\w)", normalized):
            codes.append(room.code)
    return codes


def select_rooms(catalog, query):
    text = fold_text(query)
    codes = matching_codes(catalog, query)
    selected = list(catalog.room_types)
    areas = re.findall(r"\bkhu\s+([ab])\b", text)
    if codes:
        selected = [room for room in selected if room.code in codes]
    elif areas:
        selected = [room for room in selected if set(areas) & {a.lower() for a in room.area_ids}]
    capacities = re.findall(r"\b(\d+)\s*(?:nguoi|sinh vien|sv)\b", text)
    if capacities:
        wanted = {int(v) for v in capacities}
        selected = [room for room in selected if wanted & set(room.capacities)]
    if "nau an" in text and not codes and "nau an khong" not in text:
        cooking = not bool(re.search(r"khong\s+(?:(?:duoc|cho phep|can)\s+)?nau an", text))
        selected = [room for room in selected if room.cooking_allowed is cooking]
    if "giuong tang" in text:
        selected = [room for room in selected if room.bed_type == "bunk"]
    if "giuong bo" in text:
        selected = [room for room in selected if room.bed_type == "single"]
    low, high = _prices(text)
    # Semester fees must never be treated as monthly rent.
    monthly_unconfirmed = bool("thang" in text and (low is not None or high is not None))
    if not codes:
        selected = [room for room in selected if (monthly_unconfirmed and room.price_period != "monthly") or ((low is None or room.price >= low) and (high is None or room.price <= high))]
    monthly_unconfirmed = monthly_unconfirmed and any(room.price_period != "monthly" for room in selected)
    selected.sort(key=lambda room: (room.price, room.id))
    return selected, monthly_unconfirmed


def answer_ktx(query, body, chat_repo, embedder, started):
    if not hasattr(chat_repo, "engine"):
        return None
    categories = question_categories(query)
    # Keep compound legal questions in the existing legal evidence workflow.
    if any(category != "student_housing" for category in categories):
        return None
    preliminary = fold_text(query)
    if "student_housing" not in categories and not re.search(r"\b(?:a\d+|pa\d+|pb\d+|pt\d+|bch\d+)\b", preliminary):
        return None
    repo = KtxRepository(chat_repo.engine)
    try:
        if not repo.available():
            return None
        catalog = repo.catalog()
        if catalog is None:
            return None
        embedded = embedder.embed_query(query)
        normalized = fold_text(query)
        current_codes = matching_codes(catalog, body.message)
        selection_query = body.message if current_codes else query
        sources = []
        evidence = {}
        source_map = {source.id: source for source in catalog.sources}

        def cite(source_id, content, title=None, url=None):
            source = source_map.get(source_id)
            key_url = url or (source.url if source else None)
            name = title or (source.title if source else source_id)
            prior = next((item for item in sources if item.title == name and item.source_url == key_url), None)
            if prior:
                if content not in evidence[prior.rank]:
                    evidence[prior.rank].append(content)
                    prior.excerpt = "\n\n".join(evidence[prior.rank])[:1800]
                return prior.rank
            rank = len(sources) + 1
            if rank > 5:
                return sources[0].rank
            sources.append(ChatSource(kind="dormitory", rank=rank, similarity_score=1.0, title=name,
                source="ctu_ktx_catalog", source_url=key_url, category="student_housing",
                heading="Danh mục KTX · cập nhật " + catalog.updated_at, excerpt=content[:1800],
                page_kind="web_excerpt" if key_url else "editorial_guidance"))
            evidence[rank] = [content]
            return rank

        is_map = any(term in normalized for term in ("gps", "toa do", "ban do", "o dau", "vi tri", "duong di", "chi duong"))
        wants_rooms = bool(current_codes or matching_codes(catalog, query) or re.search(r"\d+\s*(?:nguoi|sinh vien|sv)\b", normalized)
                           or any(term in normalized for term in ("loai phong", "tim ktx", "phong nau", "phong duoc", "phong khong", "giuong tang", "giuong bo", "re nhat", "duoi ")))
        wants_availability = any(term in normalized for term in ("con cho", "con trong", "het cho", "con phong", "cho trong"))
        lines = [f"**KTX · năm học {catalog.academic_year}**"] if catalog.academic_year else []
        no_answer = False
        mode = "ktx_structured"
        physical=[room for room in catalog.rooms if re.search(r"\bphong\s+"+re.escape(fold_text(room.number))+r"\b",normalized)]
        areas=re.findall(r"\bkhu\s+([ab])\b",normalized)
        if areas:
            physical=[room for room in physical if room.dormitory_id.lower() in areas]
        if physical and not is_map:
            types={room.id:room for room in catalog.room_types}
            for room in physical[:5]:
                kind=types[room.room_type_id]
                status={'unknown':'chưa xác nhận','available':'còn chỗ','full':'hết chỗ','maintenance':'bảo trì'}[room.status]
                content=(f'Khu {room.dormitory_id}, dãy {room.building}, phòng {room.number}: sức chứa {room.capacity} người. '
                    +room_text(kind,catalog.academic_year)+f' Tình trạng nhập thủ công: {status}; chỗ trống {room.available_beds if room.available_beds is not None else "chưa biết"}; '
                    f'ngày {room.verified_at or "chưa ghi nhận"}. {room.notes}')
                rank=cite('__admin_room_snapshot',content,title='Danh mục phòng KTX · ghi nhận thủ công')
                lines.append(f'- {content} [{rank}]')
            lines.append('Xác nhận lại với văn phòng KTX; dữ liệu ghi nhận không bảo đảm còn chỗ ngay lúc hỏi.')
        elif is_map:
            areas = re.findall(r"\bkhu\s+([ab])\b", normalized)
            for area in catalog.dormitories:
                if areas and area.id.lower() not in areas:
                    continue
                p = area.location
                content = f"{area.name}: {p.lat:.7f}, {p.lng:.7f} — {p.label}. Điểm đại diện từ OpenStreetMap; chưa xác nhận cổng vào hoặc vị trí từng phòng."
                rank = cite("osm-" + area.id, content, title=p.label + " · OpenStreetMap", url=p.source_url)
                lines.append(f"- {content} [{rank}]")
            lines.append("Bạn có thể mở vị trí và chỉ đường trên trang KTX của hệ thống.")
        elif wants_availability:
            fact = next(fact for fact in catalog.facts if "availability" in fact.tags)
            contact = next(fact for fact in catalog.facts if "contact" in fact.tags)
            areas=re.findall(r"\bkhu\s+([ab])\b",normalized)
            codes=matching_codes(catalog,query)
            types={room.id:room for room in catalog.room_types}
            inventory=[room for room in catalog.rooms if (not areas or room.dormitory_id.lower() in areas)
                and (not codes or types[room.room_type_id].code in codes)]
            if any(term in normalized for term in ('con cho', 'con trong', 'cho trong')) and not any(term in normalized for term in ('het cho', 'het phong')):
                inventory=[room for room in inventory if room.status=='available']
            elif any(term in normalized for term in ('het cho', 'het phong')):
                inventory=[room for room in inventory if room.status=='full']
            for room in inventory[:5]:
                status={'unknown':'chưa xác nhận','available':'còn chỗ','full':'hết chỗ','maintenance':'bảo trì'}[room.status]
                content=(f'Khu {room.dormitory_id}, dãy {room.building}, phòng {room.number}, loại {types[room.room_type_id].code}: '
                    f'{status}, số chỗ trống {room.available_beds if room.available_beds is not None else "chưa biết"}; ngày ghi nhận {room.verified_at or "chưa ghi nhận"}. '
                    'Thông tin nhập thủ công, không xác nhận chỗ trống ngay lúc hỏi.')
                rank=cite('__admin_room_snapshot',content,title='Danh mục phòng KTX · ghi nhận thủ công')
                lines.append(f'- {content} [{rank}]')
            if not inventory and catalog.rooms:
                lines.append('- Không có phòng khớp tình trạng đã ghi nhận trong danh mục đang công bố; điều này không xác nhận tồn phòng hiện tại.')
            for item in (fact, contact):
                rank = cite(item.source_id, item.content)
                lines.append(f"- {item.content} [{rank}]")
        elif wants_rooms:
            rooms, blocked = select_rooms(catalog, selection_query)
            if not rooms:
                no_answer = True
                lines.append("Chưa tìm thấy loại phòng khớp trong danh mục hiện có. Điều này không xác nhận KTX đã hết chỗ.")
            for room in rooms[:5]:
                content = room_text(room,catalog.academic_year)
                rank = cite(room.source_id, content)
                lines.append("- " + content + f" [{rank}]")
            if len(rooms) > 5:
                lines.append(f"Đang hiển thị 5/{len(rooms)} loại khớp; xem đầy đủ và lọc thêm trên trang KTX.")
            if blocked:
                lines.append("Ngân sách theo tháng không cùng kỳ tính với đơn giá đang có; chưa thể lọc theo ngân sách này hoặc kết luận mức phí tháng.")
            lines.append("Danh mục loại phòng chưa xác nhận số chỗ trống hiện tại; cần kiểm tra với văn phòng KTX.")
        else:
            tags = set()
            groups = {
                "contact": ("lien he", "dien thoai", "email", "hotline"),
                "registration": ("dang ky", "ho so", "thu tuc", "nhan cho"),
                "refund": ("hoan phi", "tra cho", "chuyen cho", "tra phong"),
                "wifi": ("wifi", "wi-fi", "internet", "mang"),
                "parking": ("gui xe", "xe may", "xe dien", "xe dap"),
                "price": ("gia", "phi", "bao nhieu", "tien"),
                "cooking": ("nau an", "bep"),
                "rules": ("noi quy", "gio giac", "gio nghi", "hut thuoc", "ruou bia"),
                "security": ("an ninh", "an toan", "bao ve", "camera"),
                "availability": ("con cho", "con trong", "het cho", "con phong"),
                "semester": ("hoc ky", "nam hoc", "2026", "2027"),
                "amenities": ("tien ich", "tien nghi", "giat", "can tin", "sieu thi"),
                "overview": ("gioi thieu", "so sanh", "quy mo", "suc chua"),
            }
            for tag, terms in groups.items():
                if any(term in normalized for term in terms):
                    tags.add(tag)
            rows = repo.search(query, embedded.vector, kinds=["fact", "source_clause"], limit=10)
            mode = "ktx_hybrid" if embedded.vector is not None else "ktx_lexical"
            candidates = [fact for fact in catalog.facts if tags & set(fact.tags)]
            if "rules" in tags or any(term in normalized for term in ("qua dem", "nguoi ngoai", "vi pham", "bi cam")):
                sanctions = any(term in normalized for term in ("xu ly", "ky luat", "hinh thuc", "muc phat"))
                # The PDF sanction table is too large and loses column alignment in extracted text.
                # Prefer intact numbered provisions for questions about permissions and exceptions.
                rows = repo.search(query, embedded.vector, kinds=["source_clause"], source_ids=["rules"],
                                   max_chars=None if sanctions else 3000, limit=3)
                lines.append("Các điều/mục liên quan trong bản nội quy CTU đã lưu:")
                for row in rows:
                    rank = cite(row["source_id"], row["content"])
                    lines.append(f"- {row['content']} [{rank}]")
                lines.append("Đây là trích đoạn nguồn công khai đã lưu; cần đối chiếu văn phòng KTX nếu có quy định mới hơn.")
            elif candidates:
                order = {row["id"]: i for i, row in enumerate(rows)}
                candidates.sort(key=lambda fact: order.get("fact-" + fact.id, 100))
                for fact in candidates[:4]:
                    rank = cite(fact.source_id, fact.content)
                    lines.append(f"- {fact.title}: {fact.content} [{rank}]")
            else:
                for row in rows[:3]:
                    excerpt = row["content"][:650].rsplit(". ", 1)[0].strip()
                    rank = cite(row["source_id"], excerpt)
                    lines.append(f"- {excerpt} [{rank}]")
            if not lines:
                return None
        response = ChatAskResponse(answer="\n".join(lines), intent="ktx_question", confidence=0.96 if sources else 0.0,
            sources=sources, listings=[], no_answer=no_answer, generation_provider="structured_ktx",
            retrieval_mode=mode, citation_accuracy=1.0 if sources else 0.0, citation_applicable=bool(sources),
            degraded=embedded.vector is None, degraded_reasons=[embedded.degraded_reason] if embedded.degraded_reason else [],
            latency_ms=max(0, int((time.perf_counter() - started) * 1000)))
        if body.include_evaluation_contexts:
            response.evaluation_contexts = [ChatEvaluationContext(kind="dormitory", rank=source.rank,
                content="\n\n".join(evidence[source.rank])) for source in sources]
        if hasattr(chat_repo, "record_event"):
            response.event_id = chat_repo.record_event(dict(intent=response.intent, confidence=response.confidence,
                no_answer=response.no_answer, degraded=response.degraded, retrieval_mode=response.retrieval_mode,
                generation_provider=response.generation_provider, result_count=len(sources), latency_ms=response.latency_ms))
        return response
    except SQLAlchemyError:
        log.warning("KTX catalogue unavailable; using existing retrieval workflow", exc_info=True)
        return None
