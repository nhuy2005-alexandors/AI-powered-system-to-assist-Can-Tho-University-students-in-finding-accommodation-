"""Evidence based dormitory advice and comparison with eligible housing rows."""
from __future__ import annotations

import logging
import re
import time

from sqlalchemy.exc import SQLAlchemyError

from .catalog import fold_text, room_text
from .chat import matching_codes, select_rooms
from .repo import KtxRepository
from ..room_service.chatbot.parser import _prices, merge_filters, parse_query
from ..room_service.chatbot.schemas import (
    ChatAskResponse, ChatConversationState, ChatEvaluationContext, ChatFilters,
    ChatListing, ChatSource,
)
from ..room_service.chatbot.topics import question_categories

log = logging.getLogger(__name__)
KTX = r"\b(?:ktx|ky tuc xa)\b"
HOUSING = r"\b(?:nha tro|phong tro|thue tro|thue ngoai|o tro)\b"


def advice_kind(query):
    text = fold_text(query)
    if not re.search(KTX, text):
        return None
    if any(category != 'student_housing' for category in question_categories(query)):
        return None
    if re.search(HOUSING, text):
        return 'ktx_comparison'
    if any(term in text for term in ('nen chon', 'phu hop', 'ngan sach', 'tu van', 'o mot minh',
                                     'o 1 minh', 'rieng tu', 've sinh rieng', 'wc rieng', 'toi uu')):
        return 'ktx_advice'
    return None


def preferences(query, body):
    """Read only user turns; the latest budget supersedes older amounts."""
    filters = ChatFilters()
    for message in [t.content for t in body.conversation_history if t.role == 'user'] + [body.message]:
        low, high = _prices(fold_text(message))
        incoming = parse_query(re.sub(KTX, '', fold_text(message))).filters
        filters = merge_filters(filters, incoming)
        if low is not None or high is not None:
            filters = filters.model_copy(update=dict(min_price=low, max_price=high,
                max_price_exclusive=bool(re.search(r'\bduoi\s*\d', fold_text(message)))))
    filters = merge_filters(filters, body.filters)
    text = fold_text(query)
    solo = bool(re.search(r'\b(?:o mot minh|o 1 minh|phong don)\b', text))
    private = bool(re.search(r'\b(?:ve sinh rieng|wc rieng|toilet rieng)\b', text))
    if re.search(r'khong (?:can|muon) (?:nha )?(?:ve sinh rieng|wc rieng|toilet rieng)', fold_text(body.message)):
        private = False
        filters = filters.model_copy(update={'amenities':[a for a in filters.amenities if a != 'private_wc']})
    cook = bool(re.search(r'\b(?:nau an|tu nau|co bep)\b', text)) and not bool(
        re.search(r'\bkhong (?:can|muon|nau|duoc nau)', text))
    group = re.search(r'\b(?:nhom (?:em |minh |toi )?(?:co )?|cho )(\d+)\s*(?:nguoi|ban)\b', text)
    people = int(group.group(1)) if group else None
    per_person = bool(people and re.search(r'\b(?:moi nguoi|tung nguoi)\b|/nguoi', text))
    # All-in budgets still cap base rent, but must never be labelled all-in matches.
    if per_person:
        filters = filters.model_copy(update={
            'min_price': filters.min_price * people if filters.min_price is not None else None,
            'max_price': filters.max_price * people if filters.max_price is not None else None})
    wants = dict(solo=solo, private=private, cook=cook, people=people, per_person=per_person,
                 privacy=solo or 'rieng tu' in text or 'yen tinh' in text,
                 safety='an toan' in text or 'an ninh' in text,
                 distance=any(term in text for term in ('vi tri', 'gan truong', 'khoang cach', 'khu ii', 'khu 2')),
                 all_costs=any(term in text for term in ('tong cong', 'tong chi', 'gom tien', 'dien, nuoc', 'dien nuoc')))
    # Amenities are checked below across both historical key conventions.
    return filters, wants


def amenity(item, *keys):
    values = item.get('parsed_amenities') or {}
    return any(values.get(key) is True for key in keys)


def criteria_met(item, filters, wants):
    # This schema has no verified occupancy limit, isolation or noise fields.
    if wants['solo'] or wants['people'] or wants['privacy']:
        return False
    requirements = {'private_wc': ('private_wc', 'private_bathroom'),
                    'fridge': ('fridge', 'refrigerator')}
    for key in filters.amenities:
        if not amenity(item, *requirements.get(key, (key,))):
            return False
    if wants['cook'] and not amenity(item, 'kitchen'):
        return False
    if wants['private'] and not amenity(item, 'private_wc', 'private_bathroom'):
        return False
    return True


def money(value):
    return f'{value:,.0f}'.replace(',', '.')


def build_advice(query, body, chat_repo, catalog, rows, filters, wants, started):
    """Render verified fields; missing amenities and capacity are not inferred."""
    compare = advice_kind(query) == 'ktx_comparison'
    sources, evidence, source_ranks = [], {}, {}
    source_map = {s.id: s for s in catalog.sources}

    def cite(source_id, content, *, title=None, url=None):
        if source_id not in source_ranks:
            # Reserve two of the five UI source slots for housing.
            if len(source_ranks) >= (3 if compare else 5):
                return None
            source = source_map.get(source_id)
            rank = len(sources) + 1
            source_ranks[source_id] = rank
            sources.append(ChatSource(kind='dormitory', rank=rank, similarity_score=1,
                title=title or (source.title if source else source_id), source='ctu_ktx_catalog', source_url=url or (source.url if source else None),
                category='student_housing', page_kind='web_excerpt' if url or (source and source.url) else 'editorial_guidance'))
            evidence[rank] = []
        rank = source_ranks[source_id]
        evidence[rank].append(content)
        sources[rank-1].excerpt = '\n\n'.join(evidence[rank])[:1800]
        return rank

    facts = {f.id: f for f in catalog.facts}
    lines = ['**KTX CTU'+(f' · năm học {catalog.academic_year}' if catalog.academic_year else '')+'**']

    def fact(fact_id):
        f = facts[fact_id]
        rank = cite(f.source_id, f.content)
        if rank:
            lines.append(f'- {f.content} [{rank}]')

    fact('fees')
    codes = matching_codes(catalog, query)
    # Add a month marker so unknown fee periods cannot be filtered as monthly rent.
    rooms, _ = select_rooms(catalog, query + ' mỗi tháng')
    if wants['solo']:
        rooms = [room for room in rooms if room.capacities == [1]]
        if not rooms:
            capacities=sorted({n for r in catalog.room_types for n in r.capacities})
            content='Sức chứa trong danh mục cập nhật: '+', '.join(str(n) for n in capacities)+' người/phòng.'
            rank=cite('submitted',content)
            lines.append('- Chưa tìm thấy loại phòng một người đáp ứng các tiêu chí đang chọn; không thể hứa bố trí ở một mình hoặc yên tĩnh tuyệt đối.'+(f' [{rank}]' if rank else ''))
    if wants['private']:
        rooms = [room for room in rooms if room.bathroom and 'rieng' in fold_text(room.bathroom)]
        if not rooms:
            a4=next((r for r in catalog.room_types if r.code=='A4' and r.source_id=='submitted'),None)
            rank=cite(a4.source_id,room_text(a4,catalog.academic_year)) if a4 else None
            lines.append('- Chưa tìm thấy loại phòng được xác nhận WC riêng đồng thời đáp ứng các tiêu chí đang chọn.'+(f' [{rank}]' if rank else ''))
    if wants['cook']:
        rooms = [room for room in rooms if room.cooking_allowed is True]
    if wants['people']:
        rooms = [room for room in rooms if wants['people'] in room.capacities]
    if wants['distance'] and not codes:
        for area in catalog.dormitories:
            p = area.location
            content = f'{area.name}: GPS {p.lat:.7f}, {p.lng:.7f}; điểm đại diện OSM, chưa xác nhận cổng/phòng.'
            rank = cite('osm-'+area.id, content, title=p.label+' · OpenStreetMap', url=p.source_url)
            if rank:
                lines.append(f'- {content} [{rank}]')
        lines.append('- Hai khu KTX nằm trong khuôn viên Khu II. Không suy ra thời gian đi bộ từ điểm đại diện.')
    if not wants['distance'] or codes:
        for room in rooms[:2]:
            content = room_text(room,catalog.academic_year)
            rank = cite(room.source_id, content)
            if rank:
                lines.append(f'- {content} [{rank}]')
        if not rooms:
            lines.append('- Chưa có loại phòng khớp các tiêu chí trong danh mục; điều này không có nghĩa KTX đã hết chỗ.')
    if wants['all_costs']:
        for key in ('utilities', 'parking', 'wifi'):
            fact(key)
        lines.append('- Chưa đủ đơn giá điện, nước, Wi-Fi và mức sử dụng để tính tổng chi mỗi tháng; không coi Wi-Fi là miễn phí.')
    if wants['safety']:
        fact('security')
    if wants['privacy']:
        fact('quiet')
    if wants['people']:
        fact('registration')
        lines.append('- Đăng ký nhóm không bảo đảm được xếp cùng phòng; cần văn phòng xác nhận.')

    exact = [item for item in rows if criteria_met(item, filters, wants)]
    selected = (exact or rows)[:2] if compare else []
    models = []
    if compare:
        lines.extend(['', '**Nhà trọ trong bộ dữ liệu hiện có**'])
        if wants['per_person'] and filters.max_price is not None:
            lines.append(f'- Ngân sách {wants["people"]} người được quy thành giới hạn tiền thuê cả phòng {money(filters.max_price)} đồng/tháng; chưa gồm chi phí khác.')
        if not exact:
            lines.append('- Chưa tìm thấy tin được xác nhận đáp ứng đủ các tiêu chí. Các ví dụ dưới đây chỉ khớp bộ lọc giá/khu vực, chưa phải lựa chọn đáp ứng đủ yêu cầu.')
        for item in selected:
            rank = len(sources) + 1
            price = item.get('price')
            content = f'{item["title"]} — ' + (f'{money(price)} đồng/phòng/tháng' if price is not None else 'chưa có giá')
            if wants['per_person'] and price is not None:
                content += f'; nếu chủ trọ cho phép {wants["people"]} người ở thì riêng tiền thuê chia đều là {money(price / wants["people"])} đồng/người/tháng'
            if item.get('distance_to_ctu') is not None:
                content += f'; khoảng cách lưu trong tin tới CTU {money(float(item["distance_to_ctu"]))} m (không phải thời gian hoặc lộ trình đã xác minh)'
            enabled = []
            for label, keys in [('nấu ăn', ('kitchen',)), ('WC riêng', ('private_wc','private_bathroom')), ('Wi-Fi',('wifi',)), ('để xe',('parking',))]:
                if amenity(item, *keys):
                    enabled.append(label)
            content += '; tiện nghi tin có nêu: '+(', '.join(enabled) or 'chưa có xác nhận')
            if str(item.get('source_id') or '').startswith(('ct_', 'nt_', 'ugc_')) or item['id'] in (1,2,3,4,5) and getattr(chat_repo, 'listing_schema', 'public') == 'public':
                content += '; TIN MẪU trong repo, không dùng làm lựa chọn thuê thực tế'
            if not criteria_met(item, filters, wants):
                content += '; CHƯA XÁC NHẬN ĐÁP ỨNG ĐỦ tiêu chí yêu cầu'
            context = content + '\nMô tả nguồn: '+str(item.get('description') or '')
            sources.append(ChatSource(kind='listing', listing_id=item['id'], rank=rank,
                similarity_score=float(item.get('similarity_score') or 0), title=item['title'],
                source=item['source'], source_url=item.get('source_url'), excerpt=context[:1800]))
            evidence[rank] = [context]
            lines.append(f'- {content}. [{rank}]')
            models.append(ChatListing(id=item['id'], corpus_schema=getattr(chat_repo,'listing_schema','public'),
                title=item['title'], price=price, area=item.get('area'), address=item.get('address'),
                district=item.get('district'), source=item['source'], source_url=item.get('source_url'),
                rank=rank, amenities=item.get('parsed_amenities') or {}, distance_to_ctu=item.get('distance_to_ctu'),
                route_time_campus=item.get('route_time_campus'), similarity_score=float(item.get('similarity_score') or 0)))
        if not selected:
            lines.append('- Không có tin đang hiển thị khớp bộ lọc; chưa đủ căn cứ nêu một phòng trọ cụ thể.')
        lines.append('- Giá tin là tiền thuê phòng theo tháng, chưa xác nhận cọc, điện nước, Wi-Fi, gửi xe hoặc số người tối đa. Nhãn tiện nghi không xác nhận chi phí đã bao gồm.')

    lines.extend(['', '**Gợi ý lựa chọn**'])
    if (wants['solo'] or wants['private']) and not rooms:
        lines.append('Ưu tiên kiểm tra nhà trọ có xác nhận '+('ở một mình' if wants['solo'] else 'WC riêng')+'; danh mục KTX chưa chứng minh đáp ứng yêu cầu này. Không khẳng định tin trọ cho ở riêng chỉ từ giá hoặc tiêu đề.')
    elif wants['safety']:
        lines.append('Chưa đủ bằng chứng để kết luận bên nào an toàn hơn. Camera/bảo vệ không bảo đảm an toàn tuyệt đối; điểm rủi ro tin không thay cho đánh giá an ninh thực tế. Kiểm tra khóa cửa, lối thoát, PCCC và người quản lý tại chỗ.')
    elif wants['distance']:
        lines.append('Nếu ưu tiên ở trong khuôn viên Khu II, hãy hỏi KTX A/B trước; nhà trọ cần đối chiếu đúng cơ sở học và đường đi thực tế. Không xếp hạng gần nhất theo tọa độ đại diện hoặc số đo chưa rõ điểm đích.')
    else:
        lines.append('Nếu ưu tiên tiết kiệm và chấp nhận ở chung, nên hỏi KTX trước để chốt biểu phí và chỗ trống; nếu ưu tiên không gian riêng, cân nhắc nhà trọ sau khi xác nhận điều kiện thuê. Cần so sánh cùng kỳ tính giá, số người và chi phí kèm theo trước khi kết luận phương án nào rẻ hơn hoặc nằm trong tổng ngân sách.')
    if wants['cook']:
        lines.append('Chỉ chọn phòng KTX cho phép nấu ăn; nhà trọ cần chủ nhà xác nhận có bếp và được phép nấu, không suy ra từ WC riêng.')
    lines.append('Cả danh mục KTX lẫn tin nhà trọ không xác nhận chỗ trống hiện tại. Liên hệ văn phòng KTX hoặc người cho thuê trước khi chuyển vào hay đặt cọc.')
    if filters.max_price is None:
        lines.append('Bạn dự kiến bao nhiêu tiền mỗi tháng, tính riêng tiền thuê hay tổng chi phí?')
    response = ChatAskResponse(answer='\n'.join(lines), intent='ktx_comparison' if compare else 'ktx_advice',
        confidence=0.85, sources=sources, listings=models, applied_filters=filters,
        partial_answer=bool(compare and not exact), no_answer=False, generation_provider='structured_housing_advice',
        retrieval_mode='ktx_housing_structured' if compare else 'ktx_advice_structured',
        citation_applicable=bool(sources), citation_accuracy=1 if sources else 0,
        latency_ms=max(0,int((time.perf_counter()-started)*1000)),
        conversation_state=ChatConversationState(filters=filters,listing_ids=[m.id for m in models]))
    if body.include_evaluation_contexts:
        response.evaluation_contexts=[ChatEvaluationContext(kind=s.kind, rank=s.rank, listing_id=s.listing_id,
            content='\n\n'.join(evidence[s.rank])) for s in sources]
    if hasattr(chat_repo,'record_event'):
        response.event_id=chat_repo.record_event(dict(intent=response.intent,confidence=response.confidence,
            no_answer=response.no_answer,degraded=False,retrieval_mode=response.retrieval_mode,
            generation_provider=response.generation_provider,result_count=len(sources),latency_ms=response.latency_ms))
    return response


def answer_advice(query, body, chat_repo, embedder, started):
    kind = advice_kind(query)
    if kind is None or not hasattr(chat_repo,'engine'):
        return None
    try:
        repo=KtxRepository(chat_repo.engine)
        if not repo.available():
            return None
        catalog=repo.catalog()
        if catalog is None:
            return None
        filters,wants=preferences(query,body)
        rows=[]
        if kind=='ktx_comparison':
            # Reuse visibility, status and SQL filters. Post-filter amenity aliases.
            retrieval_filters=filters.model_copy(update={'amenities':[],'sort_by':'price_asc','listing_ids':[]})
            rows=chat_repo.retrieve(query,retrieval_filters,None,limit=250)
            # Original demo rows remain in the 87-row dataset, but cannot support rental advice.
            if getattr(chat_repo,'listing_schema','public') == 'public':
                rows=[item for item in rows if item['id'] not in (1,2,3,4,5)]
            if wants['distance']:
                rows.sort(key=lambda item: (item.get('distance_to_ctu') is None,
                    float(item.get('distance_to_ctu') or 0),float(item.get('price') or 0)))
        return build_advice(query,body,chat_repo,catalog,rows,filters,wants,started)
    except SQLAlchemyError:
        log.warning('Dormitory advice repository unavailable',exc_info=True)
        return None
