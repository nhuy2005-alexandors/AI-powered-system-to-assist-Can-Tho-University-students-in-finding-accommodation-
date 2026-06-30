# Technical Specification: Login Feature

Xây dựng chức năng đăng nhập cơ bản và an toàn cho hệ thống. 

> [!IMPORTANT]
> **User Review Required**: Với vai trò là **@architect**, tôi đã soạn thảo bản đặc tả kiến trúc. Vui lòng xem qua các đề xuất và trả lời các câu hỏi mở bên dưới trước khi phê duyệt (approve) để chúng ta có thể chuyển giao (handoff) cho **@engineer** thực thi.

## Open Questions
1. **Tech Stack**: Hiện tại dự án dường như chưa có mã nguồn base. Bạn có muốn sử dụng **Next.js (React) + TypeScript** cho cả Frontend và Backend (API routes), hay sử dụng một kiến trúc chia tách với Backend riêng biệt (Node.js/Express, Python/FastAPI, Java/Spring Boot)?
2. **Database**: Hệ thống sẽ sử dụng cơ sở dữ liệu nào cho Users? (Tôi đề xuất: **PostgreSQL + Prisma ORM**).
3. **Phương thức Auth**: Ngoài đăng nhập bằng Email/Password truyền thống, bạn có muốn tích hợp thêm Social Login (Google, Github, Facebook) không? (Nếu dùng Next.js, có thể sử dụng **Auth.js / NextAuth** rất chuẩn bảo mật).

---

## Kiến Trúc Hệ Thống (Đề xuất: Next.js + Auth.js + PostgreSQL)

### 1. Data Model
Cấu trúc Database chuẩn cho người dùng:
- Bảng `User`: id, name, email, password_hash, role, created_at, updated_at.
- Bảng `Session`: Quản lý session tokens cho người dùng đang đăng nhập.

### 2. Frontend Components
- **Trang Đăng Nhập (`/login`)**:
  - Form nhập Email và Password với form validation (sử dụng thư viện `react-hook-form` và `zod`).
  - Xử lý trạng thái loading và hiển thị thông báo lỗi rõ ràng.
- **Layout / Middleware**: 
  - Middleware kiểm tra session ở phía server. Nếu người dùng chưa đăng nhập mà truy cập protected route, tự động redirect về `/login`.

### 3. Backend API
- **Xác thực Credential**: Nhận email/password, truy vấn database lấy `password_hash`, sử dụng `bcryptjs` để kiểm tra độ trùng khớp.
- **Quản lý Session/JWT**: Sau khi xác thực thành công, cấp phát token bảo mật (HTTP-only cookie) để định danh các request tiếp theo.

### 4. Security Requirements (Bắt buộc theo chuẩn OWASP)
- **Password Hashing**: Không bao giờ lưu mật khẩu plaintext. Phải dùng `bcrypt` (salt rounds >= 10).
- **CSRF & XSS Protection**: Các form phải bảo vệ chống CSRF, dữ liệu input phải được sanitize.
- **Rate Limiting**: Giới hạn số lần thử đăng nhập sai trên một IP để chống brute force (thông thường giới hạn 5 lần/phút).
- **Cookies**: Token phải lưu trong cookie có cờ `HttpOnly`, `Secure` và `SameSite=Strict`.

---

## Handoff Checklist cho Engineer & QA
- [ ] Khởi tạo base project với tech stack đã chốt.
- [ ] Cấu hình Database & ORM.
- [ ] Tạo bảng User & migration script.
- [ ] Implement UI Login page.
- [ ] Implement API endpoint xử lý đăng nhập.
- [ ] Viết Unit/Integration Test cho phần Auth (Yêu cầu QA coverage >= 80%).
