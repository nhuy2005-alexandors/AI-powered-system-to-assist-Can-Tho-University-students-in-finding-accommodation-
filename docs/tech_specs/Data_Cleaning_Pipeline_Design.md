# Thiết kế Pipeline Làm Sạch Dữ Liệu (Data Cleaning Pipeline)

> Ngày: 2026-07-03 · Trạng thái: Thiết kế → triển khai
> Mục tiêu: mỗi lần crawler chạy, dữ liệu thô được làm sạch tự động, cho ra bộ data
> **đáng tin, đúng đối tượng, có điểm chất lượng** để backend lọc và AI học sau này.

## 1. Vấn đề đang giải (từ đánh giá trước)

Xem `Crawler_Data_Quality_Assessment.md`. Ba lỗ gốc: (1) lẫn nhà/mặt bằng không phải trọ,
(2) 42.6% diện tích là đoán, (3) không có thước đo "tin này sạch tới đâu".

## 2. Nguyên tắc thiết kế

1. **Idempotent** — chạy lại nhiều lần cho cùng kết quả. Chỉ xử lý tin `cleaning_status='raw'`;
   tin đổi nội dung được upsert reset về `raw` (đã có).
2. **Không phá dữ liệu gốc** — mọi suy luận/đoán đều **gắn cờ**, không ghi đè mù. Giữ lại
   title gốc; chỉ bổ sung, không xoá.
3. **Phân tầng rõ ràng** — mỗi tầng một nhiệm vụ, test được độc lập.
4. **Minh bạch cho AI** — mỗi tin có `listing_type`, `quality_score`, và các cờ (`is_imputed_area`)
   để tầng AI biết tin nào tin được, tin nào cần dè chừng.

## 3. Kiến trúc 5 tầng

```
run_cleaner(engine)  — chạy sau mỗi run_source (lịch + trigger tay)
   │  lấy các tin cleaning_status='raw'
   ▼
[T1] CLASSIFY   → gán listing_type: phong_tro | nha_nguyen_can | mat_bang | khac
   ▼
[T2] VALIDATE   → reject tin rác: giá bất thường theo TỪNG loại, thiếu field bắt buộc
   ▼
[T3] AREA       → diện tích: (a) thật từ mô tả → (b) đoán theo giá; gắn is_imputed_area
   ▼
[T4] NORMALIZE  → chuẩn title (chỉ khi thiếu), điền district còn trống
   ▼
[T5] SCORE      → quality_score 0..1: đủ field + đúng đối tượng + geocode tốt + area thật
   ▼
   ghi: listing_type, cleaning_status(cleaned/rejected), quality_score,
        is_imputed_area, area, title, cleaning_logs, updated_at
```

### T1 — CLASSIFY (phân loại đối tượng)
Quyết định tin thuộc loại nào, dựa **title + giá + diện tích**:
- `mat_bang` — title chứa "mặt bằng / kho / xưởng / văn phòng / kinh doanh".
- `nha_nguyen_can` — title chứa "nhà nguyên căn / nhà mặt tiền / nguyên căn / biệt thự"
  HOẶC (giá > 6tr VÀ diện tích > 60m²).
- `phong_tro` — title chứa "phòng trọ / nhà trọ / phòng cho thuê / ký túc / ở ghép"
  HOẶC (giá ≤ 4tr VÀ diện tích ≤ 40m²).
- `khac` — không rơi vào nhóm nào.
> Cụm "nhà trọ" KHÔNG được tính là nhà nguyên căn (ưu tiên khớp "trọ" trước).

### T2 — VALIDATE (loại tin rác, theo loại)
- Thiếu giá → `rejected` (không có giá thì vô dụng cho lọc).
- `phong_tro`: giá hợp lệ 300k–8tr. Ngoài khoảng → `rejected`.
- `nha_nguyen_can` / `mat_bang`: giá 1tr–50tr (giữ lại, nhưng đánh dấu loại để backend
  lọc riêng — KHÔNG trộn vào kết quả trọ mặc định).
- `khac`: giá 300k–20tr.
- Tất cả reject đều ghi lý do vào `cleaning_logs`.

### T3 — AREA (diện tích tin cậy)
1. Đã có area thật (> 0) từ nguồn → giữ, `is_imputed_area=false`.
2. Trống → thử regex mô tả (`extract_area_from_text` — đã có, đa biến thể) → nếu ra,
   `is_imputed_area=false` (đây là số thật lấy từ text, không phải đoán).
3. Vẫn trống → đoán theo bậc giá → `is_imputed_area=true` (cờ cảnh báo).

### T4 — NORMALIZE
- Title < 15 ký tự hoặc rỗng → sinh title mô tả `"{loại} {area}m² tại {quận}"`
  **nhưng giữ title gốc** — không ghi đè nếu title gốc đủ dài.
- District trống → đã có `infer_district` ở tầng normalize crawler; tầng này chỉ điền
  "Không rõ" khi thật sự không suy được (để UI hiển thị nhất quán).

### T5 — SCORE (điểm chất lượng 0..1)
Cho backend xếp hạng, cho AI biết độ tin. Cộng điểm:
- +0.30 đúng đối tượng (`listing_type='phong_tro'`)
- +0.20 diện tích thật (không imputed)
- +0.20 geocode tốt (confidence high/medium)
- +0.15 có ảnh
- +0.10 có mô tả đủ dài (≥ 50 ký tự)
- +0.05 có đủ quận
`quality_score` = tổng, kẹp [0,1]. Tin `rejected` = 0.

## 4. Thay đổi schema (migration 70)

```sql
-- listing_type: phân loại đối tượng
CREATE TYPE listing_type_enum AS ENUM ('phong_tro','nha_nguyen_can','mat_bang','khac');
ALTER TABLE aggregated_listings
  ADD COLUMN listing_type listing_type_enum DEFAULT 'khac',
  ADD COLUMN quality_score REAL DEFAULT 0;
CREATE INDEX idx_listings_type ON aggregated_listings (listing_type);
CREATE INDEX idx_listings_quality ON aggregated_listings (quality_score DESC);
```

## 5. Tác động tới backend/AI (hợp đồng dùng)

- **Backend search** (`GET /listings`): mặc định chỉ trả `listing_type='phong_tro'` +
  `cleaning_status='cleaned'`, sắp theo `quality_score DESC` khi không có sort khác.
  Tin nhà/mặt bằng vẫn trong DB nhưng ẩn khỏi kết quả trọ mặc định.
- **AI sau này**: học/gợi ý trên tập `phong_tro` + `quality_score ≥ ngưỡng`; dùng
  `is_imputed_area` để giảm trọng số các tin diện tích đoán.

## 6. Điểm chạy (khi nào cleaner chạy)
- Sau mỗi `run_source` trong scheduler `_job` (đã có).
- Sau `POST /crawler/run` thủ công (đã có).
- Idempotent nên chạy thừa vô hại; chỉ đụng tin `raw`.

## 7. Kiểm thử
Unit test từng tầng (không cần DB): classify theo title/giá/area mẫu, validate ngưỡng theo
loại, area 3 nhánh, score cộng điểm. Integration: chạy full 6 nguồn, kiểm phân bố
listing_type + quality_score + tỉ lệ imputed.

## 8. KẾT QUẢ TRIỂN KHAI (2026-07-03, verified DB thật)

- **86 test pass** (27 cleaner unit + 59 hiện có). Cleaner idempotent (chạy lần 2 = "No raw rows").
- Xử lý 313 tin: **299 cleaned / 14 rejected**. avg quality_score = **0.84**.
- Phân loại theo nguồn:
  | nguồn | phong_tro | nha_nguyen_can | mat_bang | khac |
  |-------|-----------|----------------|----------|------|
  | phongtro123 | 211 | 0 | 16 | 8 |
  | tromoi | 17 | 1 | 0 | 0 |
  | bds123 | 7 | 0 | 1 | 1 |
  | mogi | 8 | 7 | 5 | 10 |
  | nhadatcantho247 | 4 | 4 | 5 | 6 |
- **Search giờ chỉ trả phong_tro cleaned + UGC:** total 262 (242 phong_tro + 28 user). Nhà/mặt bằng ẩn khỏi kết quả trọ mặc định. `sort=quality` hoạt động.
- quality_score histogram: 1.0→211 tin, 0.7→55, phần còn lại rải 0.4–0.9.

### Hạn chế đã biết (classifier)
- mogi & nhadatcantho247 **không skew mạnh về nha/mat_bang** như kỳ vọng — bị chia đều 4 loại,
  bucket `khac` lớn. Nguyên nhân: title 2 nguồn này không chứa keyword rõ, mà giá/diện tích
  rơi vào vùng xám (không < 4tr/≤40m² để thành phong_tro, cũng không > 6tr/>60m² để thành
  nha_nguyen_can). → nhiều tin lọt `khac` và bị ẩn khỏi search. **Chấp nhận được** (search
  vẫn sạch, chỉ mất một ít tin biên), cải thiện sau bằng: mở rộng keyword, hoặc phân loại
  từ chuyên mục URL nguồn.
- `is_imputed_area` = 0 sau lần chạy này: đa số tin đã có area thật từ nguồn (chỉ 7/313 thiếu
  area); con số 42.6% imputed trước đây là do cleaner CŨ ghi đè area đoán vào cột — data cũ
  đã "baked in", không phải bug của cleaner mới.
