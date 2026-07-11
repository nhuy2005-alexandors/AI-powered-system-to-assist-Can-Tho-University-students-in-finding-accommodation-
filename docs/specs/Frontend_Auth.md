# Đặc tả — Xác thực Frontend (Frontend Auth)

> Retrospective spec (viết sau khi code, theo khung "trước khi code" để pair với `docs/tech_specs/Frontend_Auth.md`). Tham chiếu SRS: FR-1.

## Mục tiêu

Cho phép người dùng đăng ký / đăng nhập / xem hồ sơ trên giao diện Next.js, với token
xác thực lưu an toàn (chống XSS). Frontend không tự xử lý logic xác thực — ủy quyền
toàn bộ cho FastAPI.

## Yêu cầu

Đối chiếu FR-1 (SRS §FR-1):

- [x] FR-1.2 — Đăng nhập email/password, cấp JWT (access 15p, refresh — SRS ghi 7 ngày,
  as-built dùng 30 ngày, khớp backend thật)
- [x] FR-1.5 — Quản lý hồ sơ cá nhân (trang `/me`, đọc qua `getCurrentUser()`)
- [x] FR-1.6 — Phân quyền theo role (middleware guard route theo trạng thái đăng nhập;
  role-based UI chưa mở rộng ngoài guest/user)
- [ ] FR-1.1 — Đăng ký kèm xác thực OTP: **chưa làm** — đăng ký hiện chỉ email+password,
  không có bước OTP
- [ ] FR-1.3 — Đăng nhập Google OAuth 2.0: **chưa làm**
- [ ] FR-1.4 — Quên/đặt lại mật khẩu qua email: **chưa làm**
- [x] Đăng xuất xóa cookie
- [x] Middleware chuyển hướng: chưa đăng nhập vào route bảo vệ → `/login`; đã đăng nhập
  vào `/login`, `/register` → `/me`

## Ràng buộc

- Token **không** được để JavaScript phía client đọc được (chống XSS) — bắt buộc dùng
  httpOnly cookie, không dùng `localStorage`/`sessionStorage`.
- Trình duyệt không gọi thẳng FastAPI (tránh lộ token qua network tab client, tránh
  CORS phức tạp).
- Trong container Next.js, gọi FastAPI phải qua network nội bộ Docker (`http://api:8000`),
  không phải `localhost`.
- Next.js chỉ cho ghi cookie trong Route Handler / Server Action, không ghi được lúc
  render Server Component — ảnh hưởng thiết kế luồng refresh token.
- Access token 15 phút, refresh token 30 ngày — khớp thời hạn phía backend đã có sẵn.

## Quyết định

- **httpOnly cookie qua Route Handler proxy**, không dùng localStorage: JS không đọc
  được token kể cả khi trang bị chèn mã độc XSS. Đây là quyết định cốt lõi của feature.
- **Route Handler làm proxy** (`/api/auth/login`, `/register`, `/logout`) thay vì gọi
  FastAPI trực tiếp từ client: giữ mọi request cùng-origin, backend không cần biết
  cookie.
- **Middleware chỉ kiểm tra tồn tại cookie**, không xác minh chữ ký — việc xác minh
  thật do trang tự làm khi gọi `/me`. Middleware chỉ phục vụ UX điều hướng nhanh, không
  phải lớp bảo mật chính.
- Form dùng `react-hook-form` + `zod` (thư viện thêm mới) cho validate client-side.

## Ngoài phạm vi

- OTP khi đăng ký (FR-1.1)
- Google OAuth (FR-1.3)
- Quên/đặt lại mật khẩu (FR-1.4)
- Role-based UI ngoài guest/user (admin panel, v.v.)

---
As-built chi tiết (kiến trúc, file, test đã chạy): `docs/tech_specs/Frontend_Auth.md`
