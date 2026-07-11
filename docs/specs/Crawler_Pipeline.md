# Crawler Pipeline

## Mục tiêu
Thu thập tin phòng trọ từ nhiều nguồn rao vặt BĐS Cần Thơ, chuẩn hóa, khử trùng lặp,
geocode và đưa vào DB ở trạng thái sạch — chạy tự động theo lịch, không cần can thiệp
tay, và 1 nguồn lỗi không được làm sập cả job.

## Yêu cầu
- [x] FR-3.1 Crawl batch định kỳ: incremental mỗi 5h, full sweep 3h sáng
- [x] FR-3.2 Rate-limit 1 req/5s + xoay User-Agent; 403/429 → log + bỏ nguồn, không crash job
- [x] FR-3.3 Parser plugin JSON selector theo từng nguồn (không hard-code)
- [x] FR-3.4 Chuẩn hóa giá/diện tích/tiện ích từ text tự do (regex, có fallback nội suy từ mô tả)
- [x] FR-3.5 Geocode đa tầng: Nominatim ward+district+city → landmark table → ward centroid
- [x] FR-3.6 Khử trùng MinHash/LSH cross-source, ngưỡng Jaccard 0.5
- [x] FR-3.7 Freshness: last_seen, miss_count, expired khi miss ≥ 2 (không xóa)
- [x] FR-3.8 Tính distance_to_ctu (PostGIS geom + Haversine) khi upsert
- [x] Kích hoạt tay (`POST /crawler/run`) cũng chạy cleaner ngay, không để tin kẹt `raw`
- [x] 1 nguồn lỗi (404/410/5xx) chỉ bị bỏ qua, không làm crash toàn bộ job

## Ràng buộc
- Không dùng Google Geocoding (phí) → Nominatim/OSM, usage policy ≤ 1 req/s, User-Agent định danh.
- `source_id` giới hạn `VARCHAR(100)` trong DB → slug dài phải hash MD5 (32 ký tự).
- Không xóa tin cũ, chỉ chuyển trạng thái `expired` (giữ lịch sử, không mất audit trail).
- Nominatim không parse được prefix hành chính (Phường/Quận/Đường) → phải strip trước khi query.

## Quyết định
- **Config-driven parser**: mỗi nguồn 1 file JSON selector, thêm nguồn mới không sửa code —
  vì mỗi trang rao vặt có cấu trúc HTML khác nhau và đổi theo thời gian.
- **Multi-phase pipeline** (list → detail → geocode → upsert → clean): mỗi phase tách trách
  nhiệm riêng, 1 phase lỗi không kéo sập phase khác.
- **Geocode fallback 4 tầng** thay vì chỉ gọi Nominatim 1 lần — nhiều địa chỉ nguồn thiếu/sai,
  có tọa độ cấp quận/landmark còn hơn 0 tọa độ (tin biến mất khỏi bản đồ).
- **Cleaner chạy cả ở kích hoạt tay, không chỉ ở scheduler** — bản đầu chỉ gắn vào lịch khiến
  data test/kích hoạt tay kẹt mãi ở `raw`.
- **Bắt riêng `HTTPStatusError` (404/410/5xx) ở tầng pipeline** để bỏ qua đúng 1 nguồn lỗi,
  không để exception văng lên làm chết cả crawl run — từng có 1 nguồn (bds123) crash toàn job.

## Ngoài phạm vi
- Proxy / anti-bot rotation (chỉ cần khi nguồn siết chặn hơn rate-limit hiện tại).
- Suy luận quận cho địa chỉ quá ngắn không chứa tên quận nào (chấp nhận để trống).
- Real-time crawl — hệ thống là near-fresh batch (5h/lần), không phải streaming.

---
As-built: docs/tech_specs/Crawler_Pipeline.md (+ docs/tech_specs/Crawler_Pipeline_Hardening.md)
