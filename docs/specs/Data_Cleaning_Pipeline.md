# Spec: Data Cleaning Pipeline

> Liên quan: FR-3.4 (SRS) — chuẩn hóa giá/diện tích/tiện ích từ text tự do (NLP).

## Mục tiêu
Sau mỗi lần crawler chạy, tự động làm sạch tin thô (`cleaning_status='raw'`) thành bộ
data đáng tin, đúng đối tượng (phòng trọ), có điểm chất lượng — để backend lọc và
tầng AI học sau này dùng được ngay, không cần xử lý tay.

## Yêu cầu
- [x] Phân loại `listing_type`: `phong_tro` / `nha_nguyen_can` / `mat_bang` / `khac`,
  dựa trên title + giá + diện tích.
- [x] Validate giá theo TỪNG loại (ngưỡng khác nhau), reject tin thiếu giá hoặc giá
  bất thường; ghi lý do reject vào `cleaning_logs`.
- [x] Diện tích tin cậy: ưu tiên số thật (từ nguồn hoặc regex mô tả) trước khi đoán
  theo bậc giá; gắn cờ `is_imputed_area` khi phải đoán.
- [x] Chuẩn hoá `title` khi thiếu/quá ngắn (< 15 ký tự), giữ nguyên title gốc nếu đủ dài
  — không ghi đè mù.
- [x] Tính `quality_score` 0..1 (đúng đối tượng, diện tích thật, geocode tốt, có ảnh,
  mô tả đủ dài, đủ quận) để backend sort và AI biết độ tin.
- [x] Idempotent: chỉ đụng tin `raw`; chạy lại nhiều lần không đổi kết quả.
- [x] Backend `GET /listings` mặc định chỉ trả `phong_tro` + `cleaned`, ẩn nhà/mặt bằng
  khỏi kết quả trọ mặc định (không xoá khỏi DB).
- [x] Unit test từng tầng (classify/validate/area/score) không cần DB.

## Ràng buộc
- Không phá dữ liệu gốc: mọi suy luận/đoán chỉ gắn cờ, không ghi đè field gốc.
- Chạy đồng bộ ngay sau `run_source` (scheduler + trigger tay `POST /crawler/run`),
  không cần queue/worker riêng.
- Không phụ thuộc dịch vụ NLP ngoài (regex + rule-based đủ cho quy mô hiện tại).

## Quyết định
- **5 tầng tuyến tính** (classify → validate → area → normalize → score) thay vì một
  hàm lớn: mỗi tầng một nhiệm vụ, test độc lập, dễ chỉnh ngưỡng riêng lẻ.
- **Rule-based theo keyword + ngưỡng giá/diện tích** thay vì model NLP/ML: dữ liệu ít
  (~300 tin/run), rule đủ chính xác và không cần train/maintain model.
- **Ẩn ở tầng backend query, không xoá ở tầng cleaner**: nhà/mặt bằng vẫn nằm trong DB
  (`listing_type` khác `phong_tro`) để không mất dữ liệu, chỉ ẩn khỏi search mặc định.
- **`quality_score` là điểm cộng dồn có trọng số cố định**, không dùng model xếp hạng:
  đủ minh bạch để debug, dễ hiểu cho AI tầng sau dùng làm feature.
- Migration riêng (70_listing_classify.sql) thêm `listing_type` + `quality_score`
  thay vì tái dùng cột cũ, để không phá dữ liệu 60_data_cleaning.sql đã có.

## Ngoài phạm vi
- Cải thiện classifier cho `mogi` / `nhadatcantho247`: hai nguồn này không có keyword
  title rõ, giá/diện tích rơi vùng xám → nhiều tin lọt `khac` (bị ẩn khỏi search).
  Đã verify: KHÔNG làm mất tin `phong_tro` thật (chỉ mất tin biên chưa phân loại được),
  nên chấp nhận được ở phiên này. Cải thiện sau bằng mở rộng keyword hoặc phân loại theo
  chuyên mục URL của nguồn.
- Model NLP/ML cho classify hoặc chuẩn hoá text (dùng rule-based cho tới khi rule không
  còn đủ).
- Cho phép user chỉnh ngưỡng giá/diện tích qua config/UI (đang hard-code trong pipeline).

---
As-built: xem `docs/tech_specs/Data_Cleaning_Pipeline_Design.md` (kiến trúc chi tiết,
migration SQL, kết quả verify trên DB thật).
