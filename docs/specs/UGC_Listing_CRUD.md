# Spec — UGC Listing CRUD (Người dùng tự đăng tin)

## Mục tiêu
Cho phép user đã đăng nhập tự đăng, sửa, ẩn tin phòng trọ của chính mình, dùng chung
bảng và pipeline geocode với tin crawler, phân biệt qua `source='user'` / `posted_by`.

## Yêu cầu
- [x] `POST /listings` — user đăng nhập tạo tin mới, `source='user'`, `posted_by=user.id`
- [x] `PUT /listings/{id}` — cập nhật một phần (partial update), chỉ chủ tin hoặc admin
- [x] `DELETE /listings/{id}` — ẩn tin (soft-delete), không xóa dòng khỏi DB
- [x] Ownership check: `posted_by == current_user.id` OR `role == 'admin'`, ngược lại → 403
- [x] Tin không tồn tại → 404
- [x] Tin `status='hidden'` biến mất khỏi `GET /listings`, `/nearby`, và trả 404 ở `/{id}`
- [x] Geocode tái dùng module `Geocoder` của crawler khi có địa chỉ (không viết lại)
- [x] SQL dùng tham số ràng buộc (`:param`); whitelist cột được update cố định

## Ràng buộc
- Không tự động xóa dữ liệu (P2, SRS §2.3) → chỉ đặt `status='hidden'`, giữ lại để audit/khôi phục
- Chống SQL injection: không nối chuỗi giá trị người dùng vào câu SQL (NFR-2)
- Không nhận tên cột tùy ý từ client khi update (whitelist `_UPDATABLE_COLS`)
- Không phá vỡ 3 endpoint đọc đã có sẵn (`GET /listings`, `/nearby`, `/{id}`)
- Không thêm bảng mới — dùng chung `aggregated_listings` với crawler, chỉ thêm enum qua migration

## Quyết định
- Dùng chung bảng `aggregated_listings` (không tách bảng riêng cho UGC) — tránh join khi
  tìm kiếm/hiển thị; phân biệt nguồn qua `source` + `posted_by` (NULL với tin crawler).
- Soft-delete bằng `status='hidden'` (thêm enum value ở migration `50_ugc.sql`) thay vì
  cột `is_deleted` riêng — tái dùng cơ chế lọc `status` đã có sẵn cho `expired`/`flagged`.
- Tái dùng `Geocoder` của crawler thay vì viết geocode riêng — tránh trùng logic, cùng
  nguồn Nominatim free-tier (NFR-6), bảo vệ bằng `CASE` trong SQL khi `geom` là NULL.
- Ownership check đơn giản (so sánh `posted_by`, không cần bảng permission riêng) — đủ
  cho quy mô đề tài, không cần RBAC phức tạp.

## Ngoài phạm vi
- Duyệt/kiểm duyệt tin UGC trước khi hiển thị (tin lên công khai ngay sau `POST`)
- Upload ảnh cho tin UGC
- Thông báo cho user khi admin sửa/ẩn tin của họ
- Rate-limit riêng cho `POST /listings` (dựa vào rate-limit API chung, NFR-2)

---
> **As-built:** `docs/tech_specs/UGC_Listing_CRUD.md` — implementation, file thay đổi, 7 test e2e (pass với DB thật).
>
> **Ghi chú:** SRS (`docs/planning/SRS.md`) chưa có FR riêng cho "user tự đăng tin" — chỉ
> nhắc ở §2.2 (Actor User: "đăng tin"). Feature này lấp khoảng trống đó, không map vào FR-3
> (FR-3 là crawler pipeline, khác luồng UGC).
