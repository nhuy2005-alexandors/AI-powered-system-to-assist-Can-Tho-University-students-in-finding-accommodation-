# Prompt giao Gemini agent — tăng volume crawl (Sprint 1 gate ≥3000 unique listing)

Trạng thái hiện tại: 2 nguồn (phongtro123 = 235, tromoi = 18) → 253 tin, geocode 99.6% ≥medium, 0 cross-source dup.

3 task độc lập tăng volume. Mỗi prompt = [PROMPT CHUNG] + [TASK N]. Dán prompt chung trước, rồi 1 task.

Độ khó: Task 3 (dễ, đổi số trang) < Task 1 (nguồn mới, rủi ro chặn) < Task 2 (reverse AJAX, rủi ro ToS/client-render).

---

## PROMPT CHUNG (dán đầu mỗi prompt)

```
# CONTEXT DỰ ÁN — crawler config-driven (đọc kỹ trước khi làm)

Repo: hệ thống tổng hợp phòng trọ sinh viên (FastAPI + PostgreSQL/PostGIS).
Crawler ở: apps/api/app/crawler/

## Kiến trúc parser (KHÔNG sửa parser.py trừ khi bắt buộc — thêm SOURCE mới = thêm 1 file JSON config)

parser.py đọc config JSON trong apps/api/app/crawler/sources/<source>.json.
2 chế độ item:
  - "thumb_parent": selector "item" trỏ thumbnail, card thật = node.parent (phongtro123)
  - "self": selector "item" LÀ card chứa đủ field (tromoi)

source_id: lấy theo thứ tự — regex "source_id_pattern" trong selectors → regex pr(\d+).html → chuỗi số ≥5 ký tự → slug cuối URL → md5(url).

Detail page: parse_detail_page đọc JSON-LD schema.org trước (@type Hostel/Product/Place/Apartment/Offer, lấy name/description/address.streetAddress). Không có JSON-LD → fallback CSS theo config "detail": {title, address, price, description_body, images, images_attr, images_filter}.
images_filter = substring bắt buộc có trong URL ảnh (lọc icon/logo). images_attr mặc định "src", lazy-load thường "data-src".

## Selector cú pháp
"tag.class" → text. "tag.class::attr(href)" → attribute. Nhiều selector fallback: "a, b, c" (dùng cái đầu khớp).

## Config mẫu (tromoi.com — item_mode self, KHÔNG JSON-LD):
{
  "source": "tromoi",
  "base_url": "https://tromoi.com",
  "list_url": "https://tromoi.com/tim-tro-tai-can-tho",
  "list_page_param": "",
  "incremental_pages": 1, "full_pages": 1, "max_detail_incremental": 20,
  "use_jsonld": false, "item_mode": "self",
  "selectors": {
    "item": ".hostel-item", "item_anchor": ".hostel-item__link",
    "item_url_attr": "href", "title": ".hostel-item__title",
    "price": ".hostel-item__price", "district": ".hostel-item__address",
    "thumb": ".hostel-item__img img"
  },
  "detail": {
    "title": "h1", "address": ".box-address", "price": ".value-wrap",
    "description_body": ".content-detail",
    "images_filter": "/storage/uploads/", "images_attr": "src", "images": "img"
  }
}

## Config mẫu (phongtro123 — thumb_parent + JSON-LD):
list_url có "list_page_param": "?page={page}", full_pages: 15. selectors.item = ".post__listing .post__thumb", item_anchor "a.line-clamp-2", price "span.text-green.fw-semibold", district "a.text-body". detail dùng JSON-LD (use_jsonld true) + description_body "div.border-bottom.pb-3.mb-4", images_attr "data-src".

## RÀNG BUỘC BẮT BUỘC
- P1: 0đ chi phí. CẤM API trả tiền (Google Maps...). Geocode chỉ Nominatim/OSM free.
- Tôn trọng ToS + robots.txt. Rate-limit đã có sẵn: 1 req / 5s, xoay User-Agent. 403/429 → BlockedError (bỏ nguồn, không phá pipeline). KHÔNG bypass chặn, KHÔNG stealth.
- Reproducible (đề tài NCKH): mọi thứ phải là CODE trong repo, chạy lại ra kết quả giống. KHÔNG ghi DB thủ công.

## CÁCH TEST (offline, không cần mạng)
1. Lưu HTML thật vào apps/api/tests/fixtures/<source>_list.html + <source>_detail.html.
2. Thêm fixture vào apps/api/tests/conftest.py.
3. Thêm test vào apps/api/tests/test_crawler.py: parse_list_page ra đúng N item, field title/price/district có; parse_detail_page ra address + images.
4. Chạy: cd apps/api && python -m pytest -q (phải PASS hết).

## CÁCH VERIFY NET THẬT (cần mạng, KHÔNG ghi DB)
cd apps/api && python -m app.crawler.smoke <source>
→ fetch 1 trang list + 3 detail đầu, in title/giá/địa chỉ/geocode/ảnh.

## CÁCH CRAWL THẬT GHI DB (chỉ khi Docker chạy)
docker exec nckh-api-1 python -c "import asyncio; from app.crawler.pipeline import run_source; from app.crawler.repo import ListingRepo; from sqlalchemy import create_engine; from app.config import settings;
async def main():
 eng=create_engine(settings.database_url,pool_pre_ping=True)
 print(await run_source('<source>','full',ListingRepo(eng)))
asyncio.run(main())"

## OUTPUT MONG ĐỢI
Báo cáo: file nào tạo/sửa, số item parse được, kết quả pytest, kết quả smoke (nếu chạy net). KHÔNG commit trừ khi được yêu cầu.
```

---

## PROMPT 1 — Thêm nguồn crawl mới

```
[DÁN PROMPT CHUNG Ở TRÊN TRƯỚC]

# TASK 1: Thêm 1 nguồn tin phòng trọ Cần Thơ mới

Mục tiêu: tăng volume listing (Sprint 1 gate ≥3000 unique). Hiện có 2 nguồn (phongtro123, tromoi = 253 tin).

## Bước
1. Chọn 1 nguồn free, cho phép crawl, có nhiều tin trọ Cần Thơ. Ứng viên (tự kiểm tra robots.txt + ToS trước):
   - bds123.vn / muaban.net.vn / nhatot / rongbay / dothi.net
   - Ưu tiên nguồn: (a) HTML tĩnh (không JS-render), (b) có category "phòng trọ" lọc theo Cần Thơ, (c) robots.txt không cấm path list.
   - NẾU nguồn bị 403 hard-block hoặc robots cấm → BỎ, chọn nguồn khác. Ghi lý do loại vào báo cáo.

2. Fetch HTML thật 1 trang list + 1 trang detail (curl hoặc python httpx với User-Agent trình duyệt). Lưu vào apps/api/tests/fixtures/<source>_list.html và <source>_detail.html.

3. Phân tích HTML: tìm selector thật cho item/title/price/district/url/thumb (list) và address/images/description (detail). Kiểm tra có JSON-LD schema.org không (grep 'application/ld+json').

4. Tạo apps/api/app/crawler/sources/<source>.json theo mẫu. Chọn item_mode + use_jsonld đúng. Nếu ID nguồn là số → set "source_id_pattern" trong selectors (regex có 1 group bắt ID).

5. Thêm fixture vào conftest.py + test vào test_crawler.py (theo mẫu test tromoi dòng 52-79). Chạy pytest, phải pass.

6. Verify net thật: python -m app.crawler.smoke <source>. Dán output.

7. Bật nguồn: thêm "<source>" vào ENABLED_SOURCES trong apps/api/app/crawler/scheduler.py (dòng 13).

## KHÔNG được
- Không bypass chặn. Nguồn chặn → loại, chọn khác.
- Không sửa parser.py trừ khi cấu trúc nguồn hoàn toàn khác 2 mode hiện có (nếu phải sửa → giải thích rõ tại sao, giữ backward-compat 2 nguồn cũ, chạy lại full pytest).

Báo cáo: nguồn chọn + lý do, selector tìm được, số item parse, pytest pass, smoke output.
```

---

## PROMPT 2 — Fix tromoi pagination AJAX

```
[DÁN PROMPT CHUNG Ở TRÊN TRƯỚC]

# TASK 2: Lấy full listing tromoi.com (hiện chỉ 21 tin/trang, phân trang AJAX)

Vấn đề: tromoi.com/tim-tro-tai-can-tho trả 21 tin HTML tĩnh trang 1. Nút "xem thêm"/phân trang load bằng AJAX → parser tĩnh dừng ở trang 1. Cần lấy hết (~vài trăm tin CT).

## Bước
1. Mở tromoi.com/tim-tro-tai-can-tho trên trình duyệt, DevTools → Network → XHR/Fetch. Bấm "xem thêm"/chuyển trang. Bắt request AJAX: URL endpoint, method (GET/POST), params (page, city_id, limit...), response format (JSON hay HTML fragment).

2. Reproduce endpoint bằng curl/httpx. Xác nhận đổi param page → ra tin khác. Tìm cách biết tổng số trang (total count trong response? hoặc lặp tới khi rỗng).

3. Tùy response format:
   - JSON: cần parser riêng cho tromoi (JSON → RawListing). Viết vào parser.py hàm mới hoặc nhánh theo config flag "list_format": "json" — GIỮ backward-compat các nguồn HTML. Map field JSON → RawListing (source, source_id, source_url, title, price_text, district, images).
   - HTML fragment: giữ parse_list_page hiện có, chỉ cần list_page_urls sinh đúng URL AJAX theo trang.

4. Sửa apps/api/app/crawler/sources/tromoi.json:
   - "list_url" = endpoint AJAX (nếu khác), "list_page_param" = "?page={page}" (hoặc đúng param bắt được).
   - "full_pages" = số trang thật (ceil(total/21)). "incremental_pages" = 2-3.
   - Nếu JSON: thêm "list_format": "json" + mapping kiểu JSON-path.

5. Test: lưu 1 response AJAX thật (JSON/HTML) vào fixtures, thêm test parse ra >1 item. Cập nhật test tromoi cũ nếu format đổi. pytest pass.

6. Verify: python -m app.crawler.smoke tromoi → confirm ra tin từ trang >1. Nếu Docker chạy, crawl full ghi DB (source='tromoi') → báo new_count.

## LƯU Ý
- Rate-limit 5s/req vẫn áp dụng cho AJAX. Nhiều trang = chậm, chấp nhận (batch job).
- Endpoint AJAX phải là API công khai tromoi tự expose cho web của họ — KHÔNG reverse private/auth API. Cần token/session bí mật → dừng, báo lại (có thể vi phạm ToS).
- Nếu AJAX render client-side hoàn toàn (không endpoint data thuần) → báo lại, có thể phải bỏ pagination tromoi và ưu tiên nguồn khác.

Báo cáo: endpoint AJAX (URL+params), format response, đổi gì trong parser/config, số trang, pytest pass, smoke/crawl output.
```

---

## PROMPT 3 — Cào sâu hết phongtro123 Cần Thơ

```
[DÁN PROMPT CHUNG Ở TRÊN TRƯỚC]

# TASK 3: Cào sâu hết listing phongtro123 khu vực Cần Thơ

Hiện: phongtro123 full_pages=15 (15 trang × 20 tin = ~300 tin/full sweep). Cần lấy HẾT tin trọ Cần Thơ.

## Bước
1. Xác định tổng số trang thật của phongtro123.com/tinh-thanh/can-tho:
   - Fetch trang 1, tìm pagination trong HTML → số trang cuối. Hoặc fetch ?page={n} tăng dần tới khi trang rỗng (0 item).
   - Ghi tổng trang + ước lượng tổng tin.

2. Kiểm sub-category (phongtro123 có thể tách "phòng trọ" / "nhà nguyên căn" / "căn hộ"). List CT gộp nhiều loại → giữ; tách URL riêng → cân nhắc thêm nhiều list_url (giữ 1 source="phongtro123", dedup lo trùng).

3. Sửa apps/api/app/crawler/sources/phongtro123.json:
   - "full_pages" = tổng trang thật.
   - "incremental_pages" giữ 2.
   - "max_detail_incremental" giữ 20 (chỉ giới hạn incremental; full sweep fetch detail hết — pipeline.py dòng 91: full mode max_detail = len(listings)).

4. LƯU Ý CHI PHÍ THỜI GIAN: full sweep = (số trang + số tin) × 5s. 40 trang + 800 tin ≈ 70 phút. Chấp nhận (chạy 3h sáng qua scheduler). Test thủ công giới hạn: smoke chỉ 1 trang.

5. Không đổi parser (selector phongtro123 đã đúng, 235 tin crawl OK). Chỉ đổi config số trang.

6. Verify:
   - python -m app.crawler.smoke phongtro123 → confirm vẫn parse 20 tin/trang.
   - Nếu Docker + muốn crawl full: docker exec ... run_source('phongtro123','full',...) — CHẠY NỀN vì >1h. Báo new_count.
   - pytest confirm không vỡ: cd apps/api && python -m pytest -q.

## KHÔNG được
- Không tăng full_pages quá tổng trang thật (fetch trang rỗng phí request, trigger nghi ngờ).
- Không giảm rate-limit 5s (vi phạm ToS, dễ 403).

Báo cáo: tổng trang thật, full_pages mới, có sub-category không, smoke output, (nếu chạy) new_count crawl.
```
