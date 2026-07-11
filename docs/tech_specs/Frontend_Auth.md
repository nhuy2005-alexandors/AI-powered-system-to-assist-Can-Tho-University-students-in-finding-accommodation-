# Đặc tả kỹ thuật — Xác thực Frontend (Frontend Auth)

> Ngày: 2026-07-03 · Sprint 1 · Trạng thái: **Hoàn tất, verified end-to-end**

## 1. Mục tiêu

Cho phép người dùng đăng ký / đăng nhập / xem hồ sơ trên giao diện web (Next.js), với
token xác thực được lưu **an toàn** chống tấn công XSS. Frontend không tự xử lý logic
xác thực — nó ủy quyền toàn bộ cho backend FastAPI (đã có sẵn từ Sprint 1.9).

## 2. Quyết định thiết kế cốt lõi: vì sao dùng httpOnly cookie?

| Phương án | Rủi ro | Kết luận |
|-----------|--------|----------|
| `localStorage` | JavaScript đọc được token → mã độc XSS đánh cắp được | **Loại** |
| httpOnly cookie | JS **không** đọc được cookie; chỉ trình duyệt tự đính kèm | **Chọn** |

Token (access + refresh) được lưu trong cookie gắn cờ `httpOnly`, `sameSite=lax`,
và `secure` khi chạy production. Nghĩa là kể cả khi trang bị chèn mã độc, mã đó
**không thể** đọc token để gửi đi nơi khác.

## 3. Kiến trúc: mô hình "Proxy qua Route Handler"

Trình duyệt **không bao giờ** gọi thẳng FastAPI. Thay vào đó:

```
[Trình duyệt]
    │  fetch("/api/auth/login")   ← cùng origin (localhost:3000), an toàn CORS
    ▼
[Next.js Route Handler]  (chạy phía server)
    │  gọi FastAPI qua mạng nội bộ docker: http://api:8000/auth/login
    ▼
[FastAPI]  → trả { access_token, refresh_token }
    ▲
    │  Route Handler nhận token, GHI vào httpOnly cookie rồi trả { ok: true }
    ▼
[Trình duyệt]  ← chỉ thấy { ok:true }, KHÔNG thấy token (token nằm trong cookie httpOnly)
```

Lợi ích:
- Token không bao giờ chạm tới JavaScript phía client.
- Không cần cấu hình CORS phức tạp (mọi request từ trình duyệt là cùng origin).
- Backend FastAPI giữ nguyên, không cần biết về cookie.

**Lưu ý mạng docker:** phía server (trong container `web`) phải gọi `http://api:8000`,
**không** phải `localhost:8000` (localhost trong container `web` không trỏ tới container `api`).
Biến môi trường `API_INTERNAL_URL=http://api:8000` được thêm vào `docker-compose.yml`
để phục vụ việc này.

## 4. Các thành phần & vai trò

| File | Vai trò |
|------|---------|
| `src/lib/config.ts` | Hằng số: URL API nội bộ, tên cookie, thời hạn (access 15 phút, refresh 30 ngày — khớp backend) |
| `src/lib/api.ts` | Client gọi FastAPI phía server (`login`, `register`, `refresh`, `getMe`) + kiểu `User`, `TokenPair` |
| `src/lib/session.ts` | Ghi / xóa / đọc cookie httpOnly (`setAuthCookies`, `clearAuthCookies`, ...) |
| `src/lib/current-user.ts` | `getCurrentUser()` — đọc token từ cookie, gọi `/me`; nếu access hết hạn thử refresh 1 lần |
| `src/app/api/auth/login/route.ts` | Route Handler: nhận email/mật khẩu → gọi FastAPI → ghi cookie |
| `src/app/api/auth/register/route.ts` | Tương tự cho đăng ký (kiểm tra mật khẩu ≥ 8 ký tự) |
| `src/app/api/auth/logout/route.ts` | Xóa cookie |
| `src/middleware.ts` | Bảo vệ route: chưa đăng nhập mà vào `/me` → chuyển hướng `/login`; đã đăng nhập mà vào `/login` → chuyển `/me` |
| `src/app/login/`, `register/`, `me/` | Giao diện: form (react-hook-form + zod) + trang hồ sơ |

## 5. Vòng đời token & refresh

- **Access token** sống 15 phút — dùng gọi API cần xác thực.
- **Refresh token** sống 30 ngày — dùng lấy access token mới khi access hết hạn.
- Khi `getCurrentUser()` gọi `/me` mà nhận lỗi 401 (access hết hạn), nó tự động dùng
  refresh token gọi `/auth/refresh` để lấy cặp token mới.
- **Giới hạn kỹ thuật của Next.js:** cookie chỉ được GHI trong Route Handler / Server Action,
  **không** ghi được khi đang render Server Component. Vì vậy `getCurrentUser(canRefresh=false)`
  ở trang render chỉ *đọc* (nếu cần refresh thật, thực hiện trong Route Handler). Đây là ràng buộc
  của framework, không phải lỗi thiết kế.

## 6. Vai trò của Middleware (bảo vệ route)

Middleware **chỉ kiểm tra sự tồn tại** của cookie để điều hướng UX nhanh (không xác minh
chữ ký token — việc đó do trang tự làm khi gọi `/me`). Mục đích: chặn người chưa đăng nhập
thấy trang cần bảo vệ, và đẩy người đã đăng nhập khỏi trang login/register.

Route được bảo vệ: `/me`, `/dashboard`. Route auth: `/login`, `/register`.

## 7. Kiểm thử (đã thực hiện, pass toàn bộ)

Verified trên stack docker thật (không mock):
- Đăng ký → 200, cookie httpOnly access+refresh được ghi (xác nhận cờ `HttpOnly`).
- Đăng xuất → cookie bị xóa.
- Đăng nhập lại → 200, cookie mới.
- Sai mật khẩu → 401 kèm thông báo tiếng Việt.
- Vào `/me` khi chưa đăng nhập → chuyển hướng 307 về `/login?next=/me`.
- Vào `/me` khi đã đăng nhập → render 200.

## 8. Thư viện thêm vào

`react-hook-form` (quản lý form), `zod` + `@hookform/resolvers` (kiểm tra dữ liệu nhập).

## 9. Việc tiếp theo liên quan

- Giao diện đọc danh sách/bản đồ/chi tiết phòng trọ (consume `GET /listings`).
- Form đăng/sửa tin (consume UGC CRUD — xem `UGC_Listing_CRUD.md`).
