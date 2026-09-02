# Báo cáo phòng trọ, Risk và kiểm duyệt Admin

Tài liệu này mô tả luồng đã triển khai từ lúc sinh viên báo cáo một tin đến lúc Admin xử lý.

## 1. Luồng hoạt động

```text
User đăng nhập
  → mở /listings/{id}
  → bấm “Báo cáo tin”
  → chọn lý do và nhập ghi chú
  → POST /listings/{id}/report
  → lưu reports.status = pending
  → Risk chấm lại và cộng tín hiệu cộng đồng
  → Admin mở /admin/reports và thấy báo cáo trong “Chờ xử lý”
  → Admin chọn Bác bỏ / Gắn cảnh báo / Ẩn tin
  → báo cáo và trạng thái phòng được cập nhật, Risk được chấm lại
```

Chỉ Admin thấy email, tên người báo cáo và ghi chú đầy đủ. Người dùng công khai chỉ thấy số báo cáo chưa bị bác bỏ, badge Risk và các lý do cảnh báo. Chủ tin không được tự báo cáo tin của mình.

## 2. Tín hiệu báo cáo trong Risk

- Báo cáo `pending` và `reviewed` được tính vào Risk; báo cáo `dismissed` không được tính.
- Một báo cáo cộng đồng đầu tiên cộng `0.18`; nhiều báo cáo tăng dần, tối đa `0.35`.
- Nếu có lý do `scam`, Risk cộng thêm `0.12` và hiển thị lý do nghi ngờ lừa đảo.
- Sau mỗi lần gửi hoặc kiểm duyệt báo cáo, hệ thống chấm lại Risk ngay.
- Ngưỡng badge: dưới `0.30` là an toàn, từ `0.30` đến dưới `0.60` là cẩn trọng, từ `0.60` là nghi ngờ.

## 3. Quyền và hành động Admin

Khu vực `/admin` chỉ cho tài khoản có `role=admin` truy cập. Giao diện quản trị dùng một thanh điều hướng bên trái và gồm:

- `/admin`: Dashboard tổng quan số tin, tin hoạt động, báo cáo chờ xử lý và người dùng.
- `/admin/reports`: Hàng chờ báo cáo và lịch sử kiểm duyệt.
- `/admin/listings`: Tìm kiếm, lọc và đổi trạng thái bài tin.
- `/admin/users`: Tra cứu tài khoản, vai trò, trạng thái xác minh và số hoạt động.

| Hành động | Báo cáo | Tin phòng trọ | Ảnh hưởng Risk |
|---|---|---|---|
| Bác bỏ, giữ tin | `dismissed` | `active` | Bỏ tín hiệu báo cáo |
| Gắn cảnh báo | `reviewed` | `flagged` | Giữ tín hiệu báo cáo |
| Ẩn tin | `reviewed` | `hidden` | Giữ lịch sử; tin biến mất khỏi tìm kiếm |

Khi một tin có nhiều báo cáo đang chờ, Admin xử lý một báo cáo sẽ giải quyết toàn bộ báo cáo đang chờ của cùng tin theo cùng quyết định.

## 4. API đã triển khai

| Method | Endpoint | Quyền | Công dụng |
|---|---|---|---|
| POST | `/listings/{id}/report` | User | Gửi báo cáo |
| GET | `/reports/mine` | User | Xem lịch sử báo cáo của mình |
| GET | `/admin/reports?status=pending` | Admin | Xem hàng chờ kiểm duyệt |
| PATCH | `/admin/reports/{report_id}` | Admin | Bác bỏ, gắn cảnh báo hoặc ẩn tin |
| GET | `/admin/summary` | Admin | Số liệu tổng quan cho dashboard |
| GET | `/admin/listings` | Admin | Tìm kiếm, lọc và phân trang bài tin |
| PATCH | `/admin/listings/{listing_id}/status` | Admin | Đổi trạng thái bài tin |
| GET | `/admin/users` | Admin | Tìm kiếm và phân trang người dùng |

Ví dụ payload gửi báo cáo:

```json
{
  "reason": "scam",
  "note": "Chủ tin yêu cầu chuyển khoản trước khi xem phòng"
}
```

Các giá trị `reason`: `wrong_price`, `expired`, `scam`, `other`.

Ví dụ payload kiểm duyệt:

```json
{
  "action": "flag",
  "note": "Đã kiểm tra nội dung và xác nhận cần cảnh báo"
}
```

Các giá trị `action`: `dismiss`, `flag`, `hide`.

## 5. Khởi động và cập nhật database

Với database mới, migration được chạy tự động khi volume PostgreSQL được tạo lần đầu:

```powershell
docker compose build
docker compose up -d
```

Với database cũ đã có dữ liệu, áp dụng migration một lần:

```powershell
docker compose cp infra/db/migrations/92_reports_moderation.sql db:/tmp/92_reports_moderation.sql
docker compose exec -T db psql -U nckh -d nckh -v ON_ERROR_STOP=1 -f /tmp/92_reports_moderation.sql
docker compose up -d --build
```

Migration có thể chạy lại an toàn nhờ `IF NOT EXISTS`.

## 6. Tài khoản demo cục bộ

Các tài khoản seed dùng chung mật khẩu `123456` và chỉ dành cho môi trường phát triển:

| Vai trò | Email |
|---|---|
| Admin | `admin@ctu.edu.vn` |
| User | `nguyenvana@ctu.edu.vn` |

Không sử dụng mật khẩu mẫu này ở production.

Localhost dùng `AUTH_COOKIE_SECURE=false`. Khi triển khai website bằng HTTPS, đổi thành:

```ini
AUTH_COOKIE_SECURE=true
```

## 7. Kịch bản demo với giám thị

1. Đăng nhập bằng User, mở một phòng không phải do User đó đăng.
2. Ghi lại badge và điểm/lý do Risk ban đầu.
3. Bấm **Báo cáo tin**, chọn **Nghi ngờ lừa đảo**, nhập ghi chú rồi gửi.
4. Tải lại trang chi tiết: số báo cáo tăng và Risk có thêm lý do từ cộng đồng.
5. Đăng xuất, đăng nhập bằng Admin và bấm **Quản trị** trên thanh đầu trang để mở `/admin`.
6. Chọn **Báo cáo tin** ở thanh bên trái để mở `/admin/reports`; chỉ ra người gửi, lý do, ghi chú, nội dung phòng và Risk.
7. Chọn:
   - **Bác bỏ, giữ tin** để minh họa báo cáo sai; hoặc
   - **Gắn cảnh báo** để giữ tin nhưng cảnh báo người xem; hoặc
   - **Ẩn tin** để loại tin khỏi tìm kiếm.
8. Mở các tab **Đã xác nhận** hoặc **Đã bác bỏ** để xem lịch sử kiểm duyệt.

Sau khi User đăng nhập hoặc đăng ký, hệ thống đưa họ về trang chính `/`. Trang `/me` vẫn là trang tài khoản và có các lối tắt về trang chính, bài tin của tôi và đăng tin mới.

## 8. Kiểm tra nhanh

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/openapi.json | Out-Null
```

Giao diện: `http://localhost:3000`. API docs: `http://localhost:8000/docs`.
