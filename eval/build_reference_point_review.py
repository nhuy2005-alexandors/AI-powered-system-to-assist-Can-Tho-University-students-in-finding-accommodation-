"""Publish a separate point register; never rewrite the original user answers."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

# These are source-review conclusions, not text-match replacements or prompts.
OVERRIDES={
    '1.4':('condition','optional_landlord_price_and_legal_scope','Giá điện/nước cụ thể là thông tin chủ trọ cung cấp, có thể chưa có và hỏi sau; không chấm thiếu giá trong listing là sai. Yêu cầu kiểm tra điều khoản phí trước giao kết và căn cứ giới hạn thu là phần rà riêng, không suy ra một giá mặc định.'),
    '5.4':('condition','needs_joint_conditions','Bản Word khoản 5 Điều 12 đang có dùng điều kiện thời hạn thuê dưới 12 tháng VÀ không kê khai đầy đủ số người; không đổi thành HOẶC. Còn phải đọc điều kiện hiệu lực/chuyển tiếp, chưa xác minh sự kiện kích hoạt.'),
    '9.3':('main','unsupported_progressive_water_tariff','Bảng trong bản Word QĐ215 đang có phân nhóm khách hàng/khu vực; chưa chứng minh cơ chế bậc thang theo lượng tiêu thụ hoặc tự xác định mọi phòng trọ thuộc nhóm hộ dân cư.'),
    '9.4':('illustration','unsupported_water_person_quota','Chưa có căn cứ trong nguồn đang có về định mức nước theo đầu người cho người tạm trú; không gọi là thực tiễn phổ biến khi chưa có dữ liệu có phạm vi và thời điểm.'),
    '9.5':('condition','contradicts_provided_vat_excerpt','Chú thích trong bản Word QĐ215 đang có ghi giá đã bao gồm thuế giá trị gia tăng và chưa bao gồm phí bảo vệ môi trường đối với nước thải sinh hoạt. Điều này trái mệnh đề giá chưa gồm VAT trong bản rà; vẫn cần xác nhận nguồn chính thức và kỳ hóa đơn trước khi áp dụng.'),
    '10.1':('illustration','unsupported_empirical_generalization','Không coi 30–50 nghìn hoặc 3–5 m3 là mức phổ biến; thống kê cục bộ chỉ mô tả các bản ghi có giá, đơn vị và thời điểm.'),
    '10.2':('main','needs_scope_review','Phân biệt đề nghị đối chiếu và quyền thông tin khi giao dịch với bên kinh doanh; chưa có căn cứ mọi khoản khoán phải bằng hóa đơn chia người.'),
    '11.1':('recommendation','agreement_option','Phương án để các bên thỏa thuận, không phải cách chia bắt buộc hoặc số liệu phổ biến.'),
    '11.2':('recommendation','agreement_option','Đồng hồ phụ và phân bổ nước chung là phương án thỏa thuận; không khẳng định tối ưu từ luật.'),
    '12.4':('recommendation','unsupported_internal_water_cap','Hướng dẫn tra cứu hỗ trợ đối chiếu thông tin hóa đơn của đúng nhà cung cấp; chưa chứng minh một trần thu nội bộ nước áp dụng cho mọi chủ trọ hoặc công thức chia bắt buộc.'),
    '13.3':('condition','unsupported_deadline','Điều kiện sinh sống từ 30 ngày không chứng minh thời hạn nộp trong 30 ngày; không nhận cùng con số là matched nếu khác sự kiện.'),
    '14.1':('main','needs_actor_and_data_exception','Tách nghĩa vụ công dân, hỗ trợ của chủ hộ và chứng minh chỗ ở; chủ hộ không tự đồng nhất chủ trọ; giữ ngoại lệ khai thác dữ liệu.'),
    '14.4':('illustration','outdated_reference_basis','Rà riêng NĐ282/2025, cá nhân/tổ chức và hiệu lực 15/12/2025; mức phạt không phải trọng tâm câu ai cung cấp giấy tờ.'),
    '16.1':('main','needs_separate_clauses','Điều 27/28 không đủ chứng minh hạn nộp 30 ngày hoặc tự động xóa; bổ sung Điều 29 và phân biệt căn cứ xóa với thao tác hệ thống.'),
    '16.2':('condition','needs_procedure_confirmation','Không suy ra mọi chuyển phòng cùng phường là điều chỉnh theo Điều 26; phải đọc đúng nhóm thông tin được điều chỉnh.'),
    '18.2':('condition','needs_building_classification','Số lối thoát phụ thuộc công năng, tầng, quy mô, quy chuẩn; chưa xác nhận hai lối là yêu cầu chung.'),
    '18.4':('condition','needs_equipment_standard','Không nhận ít nhất hai bình mỗi tầng là định mức chung khi chưa có loại công trình và tiêu chuẩn tương ứng.'),
    '23.1':('main','conditional_remedy','Phân biệt từ chối thuê và phí dịch vụ đã thực hiện; quyền giảm phí/chấm dứt phụ thuộc vi phạm, thỏa thuận và điều kiện.'),
    '23.2':('main','unsupported_full_refund','Chưa có căn cứ tự động hoàn 100%; Điều 519/520 BLDS hỗ trợ giảm phí/chấm dứt theo điều kiện; bồi thường cần căn cứ thiệt hại.'),
    '36.1':('recommendation','needs_basic_reporting_scope','Tập hợp thông tin và chứng cứ chung/từng người; không biến mẫu đơn tập thể có chữ ký thành điều kiện bắt buộc tiếp nhận.'),
    '36.3':('recommendation','unsupported_organized_inference','Chứng từ chuyển tiền và tin nhắn theo cùng kịch bản là thông tin để cơ quan có thẩm quyền đối chiếu; chúng không tự chứng minh tính có tổ chức/có kế hoạch để xác lập tình tiết hình sự.'),
    '36.5':('illustration','unsupported_criminal_inference','Nhiều người bị hại không tự xác lập tính chuyên nghiệp hay khung tăng nặng; giữ chứng cứ từng giao dịch, không kết luận định tội.')}

CHECKED_BASIS={
    23:[dict(source_url='https://vanban.chinhphu.vn/?docid=216125&orggroupid=4&pageid=27160',
        provision='Khoản 5 Điều 12 Thông tư 60/2025/TT-BCT trong bản Word được cung cấp',
        scope='Đối chiếu câu chữ điều kiện đồng thời và giới hạn thu theo hóa đơn; bản trích tuyển chưa được xác minh toàn bộ với nguyên bản và sự kiện kích hoạt hiệu lực chưa được xác nhận.',
        native_word='Data/electricity/Thông-tư-60-2025-TT-BCT.docx')],
    27:[dict(source_url='https://capnuoccantho2.com.vn/View.aspx?wc=63&wp=332',
        provision='Khoản 1 và 2 Điều 1 QĐ215/QĐ-UBND trong bản Word được cung cấp',
        scope='Bảng có nhóm khách hàng, khu vực, nhà cung cấp và chú thích giá đã gồm VAT; không xác nhận biểu giá đang áp dụng cho một phòng trọ/kỳ hóa đơn hoặc một định mức nước theo người.',
        native_word='Data/water_cantho/Quyết-định-215-QĐ-UBND.docx')],
    32:[dict(source_url='https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-154-2024-nd-cp-43275.htm',
        provision='Khoản 1 Điều 5 Nghị định 154/2024/NĐ-CP',
        scope='Công dân cung cấp thông tin; cơ quan khai thác dữ liệu. Khi không khai thác được, giấy tờ được cung cấp khi cơ quan có yêu cầu; không suy ra mọi hồ sơ luôn cần bản sao sổ hồng.',
        native_word='docs/legal_word_repair_corpus_v16_20261006/nd154.doc'),
        dict(source_url='https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-58-2026-nd-cp-468975/62899.htm',
        provision='Khoản 2 Điều 4 sửa điểm a khoản 3 Điều 5 Nghị định 154/2024/NĐ-CP',
        scope='Đăng ký tạm trú tại chỗ thuê, mượn, ở nhờ dùng văn bản cho thuê, cho mượn, cho ở nhờ; văn bản này không phải công chứng/chứng thực. Điều này không tự xác lập nghĩa vụ mọi chủ trọ phải ký CT01.',
        native_word='docs/legal_word_repair_corpus_v16_20261006/nd58.docx')],
    34:[dict(source_url='https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-58-2026-nd-cp-468975/62899.htm',
        provision='Khoản 7 Điều 4 sửa Điều 10 Nghị định 154/2024/NĐ-CP',
        scope='Thủ tục xóa theo từng trường hợp của Điều 29 Luật Cư trú. Hạn 07 ngày chỉ cho điểm c, e, g, h khoản 1 Điều 29; không suy ra tự động xóa hoặc hạn nộp đăng ký mới 30 ngày.',
        native_word='docs/legal_word_repair_corpus_v16_20261006/nd58.docx')],
}


def main():
    original=ROOT/'eval/datasets/external_legal_20261004/answers.json'
    manuscript=ROOT/'eval/datasets/legal_reference_point_review.txt'
    refs=json.loads(original.read_text(encoding='utf-8'))['cases']
    by_order={i+1:c for i,c in enumerate(refs)}
    notes=json.loads((original.parent/'review_20261006.json').read_text(encoding='utf-8'))
    notes={c['original_question_id']:c['review_note'] for c in notes['cases']}
    cases={i:dict(original_question_id=c['original_question_id'],question=c['question'],points=[])
           for i,c in by_order.items()}
    for line in manuscript.read_text(encoding='utf-8').splitlines():
        cells=[c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells)!=6 or not re.fullmatch(r'\d+\.\d+',cells[0]):continue
        point_id,title,importance,content,source,scope=cells
        order=int(point_id.split('.')[0]);case=cases[order]
        role='main' if 'Ý chính' in importance else 'condition' if 'Điều kiện' in importance else 'illustration'
        role,status,note=OVERRIDES.get(point_id,(role,'pending_per_point_source_verification',notes[case['original_question_id']]))
        case['points'].append(dict(point_id=point_id,title=title,manuscript_importance=importance,manuscript_content=content,
            source_claimed_in_manuscript=source,scope_and_conditions=scope,grading_role=role,
            source_review_status=status,review_note=note))
    assert len(cases)==36 and all(c['points'] for c in cases.values())
    for case in cases.values():
        case['checked_source_basis']=CHECKED_BASIS.get(case['original_question_id'],[])
        case['checked_basis_policy']='Additional source basis and limits, not a certification of every manuscript point.'
    output=ROOT/'eval/datasets/external_legal_20261004/point_review_20261006.json'
    register=dict(original_reference_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        manuscript_sha256=hashlib.sha256(manuscript.read_bytes()).hexdigest(),
        original_answers_unchanged=True,manuscript_unchanged=True,
        policy='Separate audit register. Citation labels are not proof of entailment or legal validity. Pending/unsupported claims must not become source-supported gold. Original text agreement is reported separately.',
        utility_price_policy='Landlord-supplied variables; missing electricity/water price means unknown, ask later. Do not infer or penalize absent listing prices.',
        cases=list(cases.values()))
    output.write_text(json.dumps(register,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(cases),points=sum(len(c['points']) for c in cases.values()),
        statuses=dict(Counter(p['source_review_status'] for c in cases.values() for p in c['points'])))))


if __name__=='__main__':main()
