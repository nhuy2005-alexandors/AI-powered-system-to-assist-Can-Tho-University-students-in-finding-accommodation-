from pathlib import Path
from types import SimpleNamespace
import time

import pytest

from app.ktx.advice import advice_kind, preferences, build_advice, answer_advice
from app.ktx.catalog import KtxCatalog
from app.room_service.chatbot.schemas import ChatAskRequest, ChatHistoryMessage


@pytest.fixture
def catalog():
    return KtxCatalog.model_validate_json((Path(__file__).parents[1]/'app/ktx/catalog.json').read_bytes())


def row(id=1001, price=750000, amenities=None):
    return dict(id=id,title='Phòng thử nghiệm',price=price,source='phongtro123',
        source_url='https://phongtro123.com/test',parsed_amenities=amenities or {},
        similarity_score=0.6,description='Mô tả nguồn',distance_to_ctu=2000)


def answer(catalog, question, rows=None, history=None):
    body=ChatAskRequest(message=question,conversation_history=history or [],include_evaluation_contexts=True)
    filters,wants=preferences(question,body)
    return build_advice(question,body,SimpleNamespace(listing_schema='public'),catalog,
                        rows if rows is not None else [row()],filters,wants,time.perf_counter())


@pytest.mark.parametrize('question',[
    'Dưới 1 triệu mỗi tháng nên chọn KTX hay nhà trọ?',
    'So sánh ký túc xá và phòng trọ về an ninh',
    'KTX hay thuê ngoài, em muốn ở một mình',
])
def test_comparison_intent(question):
    assert advice_kind(question)=='ktx_comparison'


def test_simple_ktx_lookup_stays_in_existing_handler():
    assert advice_kind('KTX A4 có gì?') is None
    assert advice_kind('KTX đăng ký thế nào?') is None
    assert advice_kind('Giá điện nhà trọ theo luật và KTX khác nhau thế nào?') is None
    assert advice_kind('Nhà trọ dưới 1 triệu') is None


def test_comparison_grounds_both_sides(catalog):
    result=answer(catalog,'Dưới 1 triệu mỗi tháng nên chọn KTX hay nhà trọ?')
    assert result.intent=='ktx_comparison'
    assert {s.kind for s in result.sources}=={'dormitory','listing'}
    assert {s.rank for s in result.sources}=={c.rank for c in result.evaluation_contexts}
    assert len(result.sources)<=5
    assert '750.000 đồng/phòng/tháng' in result.answer
    assert 'chưa xác nhận kỳ tính' in result.answer
    assert '285.000 đồng/người/tháng' not in result.answer


def test_private_wc_and_cooking_do_not_claim_near_misses_match(catalog):
    result=answer(catalog,'KTX hay nhà trọ dưới 1 triệu, muốn nấu ăn và WC riêng?')
    assert result.partial_answer
    assert 'A4 có WC tập thể' in result.answer
    assert 'CHƯA XÁC NHẬN ĐÁP ỨNG ĐỦ' in result.answer
    assert 'Chưa tìm thấy tin được xác nhận đáp ứng đủ' in result.answer


def test_old_and_new_private_bathroom_keys():
    from app.ktx.advice import criteria_met
    body=ChatAskRequest(message='KTX hay nhà trọ dưới 1 triệu có WC riêng')
    filters,wants=preferences(body.message,body)
    for key in ['private_wc','private_bathroom']:
        assert criteria_met(row(amenities={key:True}),filters,wants)
    assert not criteria_met(row(),filters,wants)


def test_solo_not_recommended_shared_dormitory(catalog):
    result=answer(catalog,'Em muốn ở một mình, KTX hay nhà trọ dưới 1 triệu?')
    assert 'không có loại phòng một người' in result.answer
    assert 'sức chứa 8 người' not in result.answer
    assert 'không khẳng định tin trọ cho ở riêng' in result.answer.lower()
    assert result.partial_answer


def test_group_budget_is_per_room_and_capacity_unconfirmed(catalog):
    q='Nhóm em 4 người, mỗi người dưới 1 triệu/tháng. So sánh KTX A4 với nhà trọ.'
    body=ChatAskRequest(message=q)
    filters,wants=preferences(q,body)
    assert filters.max_price==4000000 and filters.max_price_exclusive
    result=answer(catalog,q,[row(price=2000000)])
    assert '500.000 đồng/người/tháng' in result.answer
    assert 'nếu chủ trọ cho phép 4 người' in result.answer
    assert 'không bảo đảm được xếp cùng phòng' in result.answer
    assert result.partial_answer


def test_all_in_budget_is_not_claimed_affordable(catalog):
    result=answer(catalog,'Tổng cộng 1 triệu/tháng gồm tiền ở điện nước, nên ở KTX hay nhà trọ?')
    assert 'Chưa đủ đơn giá điện, nước' in result.answer
    assert 'chưa xác nhận cọc' in result.answer
    assert 'chắc chắn nằm trong tổng ngân sách' in result.answer


def test_safety_and_vacancy_are_not_guaranteed(catalog):
    result=answer(catalog,'KTX và nhà trọ dưới 1 triệu bên nào an toàn hơn, còn phòng ngay không?')
    assert 'Chưa đủ bằng chứng để kết luận bên nào an toàn hơn' in result.answer
    assert 'không xác nhận chỗ trống hiện tại' in result.answer


def test_map_comparison_keeps_both_areas(catalog):
    result=answer(catalog,'KTX A/B và nhà trọ gần trường Khu II thì vị trí thế nào?')
    assert '10.0338798' in result.answer and '10.0301622' in result.answer
    assert len(result.sources)<=5


def test_no_housing_match_does_not_fabricate_listing(catalog):
    result=answer(catalog,'KTX hay nhà trọ dưới 100k/tháng?',[])
    assert not result.listings
    assert result.partial_answer
    assert 'Không có tin đang hiển thị khớp' in result.answer


def test_new_budget_replaces_old_in_followup():
    body=ChatAskRequest(message='Còn dưới 800k thì sao?',conversation_history=[
        ChatHistoryMessage(role='user',content='KTX hay nhà trọ dưới 2 triệu?')])
    filters,_=preferences('KTX hay nhà trọ dưới 2 triệu. Còn dưới 800k thì sao?',body)
    assert filters.max_price==800000


def test_ktx_only_advice(catalog):
    result=answer(catalog,'KTX có phù hợp nếu muốn ở một mình không?')
    assert result.intent=='ktx_advice'
    assert not result.listings


def test_demo_rows_not_used_for_rental_advice(catalog,monkeypatch):
    import app.ktx.advice as module
    monkeypatch.setattr(module,'KtxRepository',lambda engine: SimpleNamespace(
        available=lambda:True,catalog=lambda:catalog))
    repo=SimpleNamespace(engine=object(),listing_schema='public',retrieve=lambda *a,**k:[row(id=5),row(id=1001)])
    body=ChatAskRequest(message='KTX hay nhà trọ dưới 1 triệu/tháng?')
    result=answer_advice(body.message,body,repo,None,time.perf_counter())
    assert [item.id for item in result.listings]==[1001]


def test_short_cooking_followup_inherits_ktx_context():
    from app.room_service.chatbot.service import rewrite_query
    history=[ChatHistoryMessage(role='user',content='KTX có phù hợp với em không?')]
    assert 'KTX' in rewrite_query('Còn nấu ăn thì sao?',history)
    assert rewrite_query('Thời tiết ngày mai thế nào?',history)=='Thời tiết ngày mai thế nào?'
