# Đặc tả kỹ thuật — UGC Listing CRUD (Người dùng tự đăng tin)

> Ngày: 2026-07-02 · Sprint 1.10 · Trạng thái: **Hoàn tất, verified với DB thật**

## 1. Mục tiêu

Cho phép người dùng đã đăng nhập **tự đăng tin** cho thuê phòng trọ, **sửa** tin của mình,
và **ẩn** (xóa mềm) tin của mình. Đây là dữ liệu do người dùng tạo (UGC — User-Generated
Content), phân biệt với tin do crawler tự thu thập.

## 2. Endpoint

| Method | Đường dẫn | Mô tả | Yêu cầu |
|--------|-----------|-------|---------|
| `POST` | `/listings` | Đăng tin mới | Đăng nhập |
| `PUT` | `/listings/{id}` | Sửa tin | Là chủ tin **hoặc** admin |
| `DELETE` | `/listings/{id}` | Ẩn tin (xóa mềm) | Là chủ tin **hoặc** admin |

Ba endpoint đọc đã có từ trước (`GET /listings`, `/nearby`, `/{id}`) — không đổi ngoài
việc lọc ẩn tin (mục 5).

## 3. Phân biệt tin người dùng vs tin crawler

Dùng chung một bảng `aggregated_listings`. Phân biệt bằng:
- `source = 'user'` (tin crawler có `source = 'mogi' | 'bds123' | ...`).
- `posted_by` = ID người đăng (tin crawler để `NULL`).

## 4. Kiểm soát quyền sở hữu (Ownership)

Khi sửa/xóa, hệ thống kiểm tra:
- Cho phép nếu `user.id == posted_by` (chính chủ), **hoặc** `role == 'admin'`.
- Ngược lại → lỗi **403** ("Không có quyền sửa/xoá tin này").
- Nếu tin không tồn tại → **404** ("Không tìm thấy tin").

## 5. Xóa mềm (Soft-delete) — quyết định quan trọng

Xóa tin **không** xóa dòng khỏi database. Thay vào đó đặt `status = 'hidden'`.

Lý do: giữ lại dữ liệu để khôi phục / audit, và tách bạch ba trạng thái ẩn:
- `expired` — crawler phát hiện tin gốc đã mất.
- `flagged` — bị đánh dấu rủi ro.
- `hidden` — **người dùng chủ động ẩn** (giá trị mới thêm ở migration `50_ugc.sql`).

**Hệ quả quan trọng (đã fix):** mọi đường đọc công khai phải ẩn cả `hidden`:
- `GET /listings` (tìm kiếm) và `/nearby` lọc `status NOT IN ('expired','hidden')`.
- `GET /listings/{id}` dùng `get_visible()` → tin đã ẩn trả **404** (không lộ ra công khai).

Nếu bỏ sót bước này, tin "đã xóa" vẫn hiển thị cho mọi người — đây là lỗi logic đã được
phát hiện qua test và sửa.

## 6. Geocode (chuyển địa chỉ → tọa độ)

Khi đăng/sửa có địa chỉ, hệ thống gọi `Geocoder` (tái dùng của crawler) để lấy
kinh/vĩ độ, tính khoảng cách tới ĐH Cần Thơ (`distance_to_ctu`), và lưu điểm địa lý (`geom`).
Nếu không có địa chỉ hoặc geocode thất bại, `geom` để `NULL` (bảo vệ bằng mệnh đề `CASE`
trong SQL để không gọi hàm tọa độ với giá trị NULL).

## 7. An toàn (Security)

- Mọi câu SQL dùng **tham số ràng buộc** (`:param`), không nối chuỗi giá trị người dùng
  → chống SQL injection.
- Danh sách cột được phép cập nhật (`_UPDATABLE_COLS`) là **whitelist cố định**, không nhận
  tên cột tùy ý từ người dùng.

## 8. Các thành phần

| File | Vai trò |
|------|---------|
| `apps/api/app/listings/schemas.py` | `ListingCreate` (title bắt buộc), `ListingUpdate` (mọi field tùy chọn — cập nhật một phần) |
| `apps/api/app/listings/repo.py` | Lớp `ListingWriteRepo`: `create` / `get_owner` / `update` / `soft_delete`; và `get_visible` (đọc ẩn tin hidden/expired) |
| `apps/api/app/listings/router.py` | 3 endpoint POST/PUT/DELETE + kiểm tra quyền |
| `infra/db/migrations/50_ugc.sql` | Thêm giá trị enum `'hidden'` + index `posted_by` |

## 9. Kiểm thử (đã thực hiện, pass toàn bộ — 7 test e2e + 59 test tổng)

Verified với PostgreSQL thật trong docker (không mock):
- Đăng tin → 201, dữ liệu lưu đúng, `posted_by` = user, `source='user'`.
- Đăng tin không đăng nhập → 403.
- Sửa tin của mình → 200, dữ liệu cập nhật.
- Sửa tin người khác → 403.
- Sửa tin không tồn tại → 404.
- Xóa tin của mình → 204, DB đặt `status='hidden'`, tin biến mất khỏi kết quả tìm kiếm & trả 404 khi xem chi tiết.
- Xóa tin người khác → 403.

## 10. Ghi chú vận hành

Migration `50_ugc.sql` được áp dụng thủ công vào DB đang chạy và thêm dòng `COPY` vào
`infra/db/Dockerfile` để lần khởi tạo cluster mới sẽ tự chạy. (Cơ chế init của Postgres
chỉ chạy script một lần lúc tạo volume rỗng.)
