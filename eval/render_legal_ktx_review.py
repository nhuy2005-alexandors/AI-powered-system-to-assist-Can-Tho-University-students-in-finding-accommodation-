"""Readable answers, source excerpts and RAGAS scores from real checkpoints."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from urllib.parse import urlparse

METRICS = ("faithfulness", "answer_relevancy", "context_utilization")
LABELS = {"housing_contract": "Hợp đồng", "electricity": "Điện", "water_cantho": "Nước",
          "residence": "Cư trú", "fire_safety": "PCCC", "student_housing": "Ký túc xá",
          "real_estate_brokerage": "Môi giới", "ecommerce_platform": "Nền tảng đăng tin",
          "privacy_data": "Dữ liệu cá nhân", "criminal_law": "Dấu hiệu lừa đảo"}


def state(case):
    if case.get("error"):
        return "Lỗi chạy"
    if "answer" not in case:
        return "Chưa chạy"
    if case.get("partial_answer"):
        return "Trả lời một phần"
    if case.get("no_answer"):
        return "Chưa đủ căn cứ"
    return "Đã trả lời · cần rà nguồn"


def score_text(value):
    return "Chưa có điểm" if value is None else str(value)


def link(source):
    title = escape(source.get("title") or "Nguồn")
    url = source.get("source_url") or ""
    if urlparse(url).scheme in {"http", "https"}:
        return '<a target="_blank" rel="noreferrer" href="' + escape(url, quote=True) + '">' + title + ' ↗</a>'
    return title


def render(data, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    cases = data["cases"]
    summary = data.get("summary", {})
    generated = sum("answer" in case for case in cases)
    identity = data.get("generation_identity", {})
    judge = data.get("judge", {})
    now = datetime.now(timezone.utc).isoformat()
    notes = [
        "Giữ nguyên 58 câu gốc, thêm 8 câu KTX thành 66. Lượt này chạy câu 19–66: 36 pháp lý và 12 KTX; không chạy 18 câu tìm tin trọ.",
        "Câu trả lời và nguồn được lấy từ hệ thống thật, không dùng đáp án sinh ra làm đáp án chuẩn.",
        "Nguồn pháp lý: bản sao riêng của legal_ctu_ktx_v2_20261007 (44 tài liệu, 530 đoạn/vector); danh mục KTX riêng có 107 bản ghi/vector.",
        "Đánh giá trên bản xem trước cổng 3001, agent và graph tắt; không thay đổi bản ở cổng 3000. Không dùng lịch sử/cache trả lời hay ghi telemetry người dùng.",
        "Faithfulness đo mức bám các đoạn nguồn; Answer Relevancy đo liên quan câu hỏi; Context Utilization đo mức hữu dụng của ngữ cảnh với phản hồi. Điểm không chứng minh luật còn hiệu lực hoặc câu trả lời đúng pháp lý.",
        "Chưa có đáp án chuẩn được người độc lập gán nhãn: không báo Answer Correctness và Context Recall. Câu lỗi/chưa chấm không được gán điểm 0.",
        "Model sinh và chấm cùng họ Gemini qua proxy nên có thể thiên lệch. Tên model là alias do proxy công bố; chưa xác minh model nền thực tế.",
        "KTX: giá bảng người dùng chưa xác nhận kỳ tính; phí CTU 2025 theo học kỳ 3,5 tháng. GPS là điểm đại diện, chưa xác nhận chỗ trống.",
    ]
    markdown = ["# Câu trả lời, nguồn và điểm RAGAS · Pháp lý & KTX", "",
                f"Cập nhật báo cáo UTC: {now}. Đã lưu {generated}/{len(cases)} câu trả lời.", "",
                f"Model trả lời: {identity.get('answer_model', 'đang khởi tạo')}; model chấm: {judge.get('model', 'chưa chấm')}; RAGAS {judge.get('version', 'chưa chấm')}.", "",
                "## Phạm vi và cách đọc", "", *["- " + note for note in notes], "",
                "## Điểm tổng hợp", "", "| Chỉ số | Trung bình | Số điểm hợp lệ |", "|---|---:|---:|"]
    for metric in METRICS:
        metric_summary = summary.get("ragas", {}).get(metric, {})
        markdown.append(f"| {metric} | {score_text(metric_summary.get('mean'))} | {metric_summary.get('scored', 0)}/{len(cases)} |")
    cards = []
    for case in cases:
        status = state(case)
        scores = case.get("ragas", {})
        warnings = []
        if case.get("degraded"):
            warnings.append("Hệ thống ghi nhận chế độ hạn chế")
        if case.get("ragas_errors"):
            warnings.append("Có lỗi chấm RAGAS")
        if any(isinstance(scores.get(metric), (int, float)) and scores[metric] < .7 for metric in METRICS):
            warnings.append("Có điểm dưới 0,7: ưu tiên đọc lại")
        if case.get("partial_answer") or case.get("no_answer") or case.get("error"):
            warnings.append(status)
        group = LABELS.get(case["category"], case["category"])
        answer = case.get("answer", case.get("error", "Chưa có câu trả lời trong checkpoint."))
        markdown.extend(["", f"## Câu {case['id']} · {group}", "", case["question"], "",
                         f"Trạng thái: {status}. Provider: {case.get('generation_provider', '—')}; model: {case.get('generation_model') or '—'}.", "",
                         " | ".join(metric + ": " + score_text(scores.get(metric)) for metric in METRICS), "", answer, "", "### Nguồn và ngữ cảnh", ""])
        source_html = []
        for index, source in enumerate(case.get("sources", [])):
            title = source.get("title", "Nguồn")
            url = source.get("source_url")
            heading = source.get("heading") or ""
            pages = str(source.get("page_from") or "")
            if source.get("page_to") and source.get("page_to") != source.get("page_from"):
                pages += "–" + str(source["page_to"])
            page_label = "Trang bản trích" if source.get("page_kind") == "logical_document" else "Trang PDF" if source.get("page_kind") == "physical_pdf" else "Trang"
            context = case.get("contexts", [])[index] if index < len(case.get("contexts", [])) else source.get("excerpt", "")
            markdown.extend([f"**[{source.get('rank')}] " + (f"[{title}]({url})" if url else title) + "**", "",
                             heading + (" · " + page_label + " " + pages if pages else ""), "",
                             "Đường dẫn nguồn: " + (source.get("source_path") or "Danh mục KTX dùng chung"), "",
                             "```text", context or "Không có trích đoạn", "```", ""])
            source_html.append('<details class="source"><summary>[' + str(source.get("rank")) + '] ' + link(source)
                               + '</summary><p>' + escape(heading) + (" · " + page_label + " " + pages if pages else "")
                               + '</p><pre>' + escape(context or "Không có trích đoạn") + '</pre></details>')
        errors = {"collect": case.get("error"), "ragas": case.get("ragas_errors"), "degraded": case.get("degraded_reasons")}
        if any(errors.values()):
            markdown.extend(["### Lỗi và giới hạn đã ghi nhận", "", "```json", json.dumps(errors, ensure_ascii=False, indent=2), "```", ""])
        details = '<details class="errors"><summary>Lỗi/giới hạn đã ghi nhận</summary><pre>' + escape(json.dumps(errors, ensure_ascii=False, indent=2)) + '</pre></details>' if any(errors.values()) else ''
        score_html = ''.join('<span><b>' + metric + '</b> ' + score_text(scores.get(metric)) + '</span>' for metric in METRICS)
        cards.append('<article class="case" data-group="' + escape(case["category"]) + '" data-review="' + str(bool(warnings)).lower() + '">'
                     + '<p class="eyebrow">Câu ' + str(case["id"]) + ' · ' + escape(group) + '</p><h2>' + escape(case["question"])
                     + '</h2><p class="status">' + escape(status) + ' · ' + escape(case.get("generation_provider") or '—') + '</p>'
                     + '<div class="scores">' + score_html + '</div>'
                     + ('<p class="warning">' + escape(' · '.join(warnings)) + '</p>' if warnings else '')
                     + '<h3>Câu trả lời đã lưu</h3><pre class="answer">' + escape(answer) + '</pre><h3>Nguồn · bấm để mở trích đoạn</h3>'
                     + ''.join(source_html) + details + '</article>')
    markdown.append("\nBáo cáo JSON gốc lưu toàn bộ provider calls, quyết định chấm, lỗi, hash dữ liệu và cấu hình không chứa khóa API.\n")
    output.with_suffix(".md").write_text("\n".join(markdown), encoding="utf-8")
    options = '<option value="">Tất cả chủ đề</option>' + ''.join('<option value="' + key + '">' + label + '</option>' for key, label in LABELS.items())
    html = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAGAS · Pháp lý & KTX CTU</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f2f6fa;color:#16314a;font:15px/1.65 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:28px 20px 60px}header{background:#06305c;color:white;padding:30px;border-radius:22px}h1{font-size:30px;margin:0}h2{font-size:20px;line-height:1.5}h3{font-size:14px}a{color:#0766ad}header a{color:#cfeeff}.toolbar{position:sticky;top:0;z-index:2;display:flex;gap:12px;flex-wrap:wrap;background:#f2f6faf5;padding:18px 0}input,select{font:inherit;min-height:44px;border:1px solid #c5d5e3;border-radius:10px;padding:8px 12px;background:white}input{flex:1;min-width:200px}.case{background:white;border:1px solid #dbe5ef;border-radius:18px;padding:24px;margin:18px 0}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#087684;font-weight:700}.scores{display:flex;gap:10px;flex-wrap:wrap}.scores span{padding:6px 10px;background:#eaf3fc;border-radius:8px;font-size:12px}.status{font-size:13px;color:#62788d}.warning{background:#fff1cf;color:#684606;padding:8px 12px;border-radius:8px}pre{font:14px/1.75 system-ui,sans-serif;white-space:pre-wrap;overflow-wrap:anywhere;margin:10px 0}.answer{border-left:3px solid #2186c4;padding-left:16px}.source,.errors{border:1px solid #dbe5ef;border-radius:10px;padding:12px;margin:10px 0}.source pre{background:#f7fafc;padding:14px}.source p{font-size:12px;color:#63788d}summary{cursor:pointer}.note{font-size:13px;color:#546b80}.notes{background:white;border-radius:14px;padding:18px;margin-top:18px}label{display:flex;align-items:center;gap:6px}label input{min-height:0;min-width:0;flex:0}small{color:#cee7ff}@media(max-width:600px){main{padding:16px 12px}header{padding:22px}h1{font-size:24px}.case{padding:18px}}@media print{.toolbar{display:none}body{background:white}.case{break-inside:avoid}details>*{display:block!important}}</style><main>'''
    html += '<header><h1>Pháp lý & KTX CTU · RAGAS</h1><p>' + str(generated) + '/' + str(len(cases)) + ' câu đã có phản hồi · Ngân hàng ' + str(data.get("bank_size", 66)) + ' câu</p><small>Model: ' + escape(str(identity.get("answer_model", "—"))) + ' · Judge: ' + escape(str(judge.get("model", "chưa chấm"))) + ' · Cập nhật UTC: ' + now + '</small></header>'
    html += '<section class="notes"><h2>Điểm RAGAS trung bình</h2><div class="scores">' + ''.join(
        '<span><b>' + label + '</b> ' + score_text(summary.get("ragas", {}).get(metric, {}).get("mean"))
        + ' · ' + str(summary.get("ragas", {}).get(metric, {}).get("scored", 0)) + '/' + str(len(cases)) + ' câu</span>'
        for metric, label in zip(METRICS, ("Bám nguồn", "Liên quan câu hỏi", "Hữu dụng ngữ cảnh"))) + '</div></section>'
    html += '<details class="notes"><summary>Phạm vi, cách đọc và giới hạn đánh giá</summary><ul>' + ''.join('<li>' + escape(note) + '</li>' for note in notes) + '</ul></details>'
    html += '<div class="toolbar"><input id="search" aria-label="Tìm câu hỏi, câu trả lời hoặc nguồn" placeholder="Tìm câu hỏi, câu trả lời, nguồn…"><select id="group" aria-label="Chủ đề">' + options + '</select><label><input id="review" type="checkbox">Ưu tiên xem lại</label><span id="count"></span></div>'
    html += ''.join(cards) + '''<script>const norm=v=>v.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d');const cards=[...document.querySelectorAll('.case')];function filter(){const q=norm(document.getElementById('search').value),group=document.getElementById('group').value,review=document.getElementById('review').checked;let n=0;for(const card of cards){const show=(!q||norm(card.textContent).includes(q))&&(!group||card.dataset.group===group)&&(!review||card.dataset.review==='true');card.hidden=!show;if(show)n++;}document.getElementById('count').textContent=n+' câu';}['search','group','review'].forEach(id=>document.getElementById(id).addEventListener('input',filter));filter();</script></main></html>'''
    output.with_suffix(".html").write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(json.loads(args.input.read_text(encoding="utf-8")), args.output)
    print(str(args.output.with_suffix(".html")))


if __name__ == "__main__":
    main()
