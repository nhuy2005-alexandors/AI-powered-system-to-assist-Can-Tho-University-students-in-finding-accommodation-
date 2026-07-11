# Handoff: Chức năng đăng nhập

**Hoàn thành [Xây dựng base project và chức năng đăng nhập]. Handoff cho @qa: [Kiểm thử chức năng đăng nhập]**

## 1. Danh sách thay đổi:
- Khởi tạo project Next.js bằng `create-next-app` tại `app_build/`
- Cài đặt và thiết lập schema cho **Prisma ORM** (`prisma/schema.prisma`), bao gồm bảng `User`, `Account`, `Session` theo chuẩn NextAuth.
- Viết API Route cho NextAuth (`src/app/api/auth/[...nextauth]/route.ts`) với cấu hình Credentials provider (sử dụng `bcryptjs` để kiểm tra password).
- Tạo trang giao diện **Đăng Nhập** (`src/app/login/page.tsx` và `src/app/login/LoginForm.tsx`) với validation chặt chẽ bằng `react-hook-form` kết hợp `zod`.

## 2. Checklist cho Testing Agent (@qa):
- [ ] Thiết lập Database test local (hoặc mock db) và thêm `DATABASE_URL`, `NEXTAUTH_SECRET` vào file `.env`.
- [ ] Chạy `npx prisma db push` để apply schema.
- [ ] Chạy Server (`npm run dev`) và đảm bảo không có lỗi compile.
- [ ] Seed một tài khoản user mẫu (mật khẩu phải được hash bằng bcrypt).
- [ ] **Kiểm thử Invalid Login**: Đăng nhập sai email/password phải hiển thị lỗi rõ ràng ("Invalid email or password").
- [ ] **Kiểm thử Empty Submission**: Form validation của Zod phải chặn không cho submit và báo đỏ.
- [ ] **Kiểm thử Valid Login**: Đăng nhập đúng phải redirect thành công và lưu session cookie HTTP-only.
- [ ] (Tuỳ chọn) Tạo Unit Test cho API Route nếu cần đạt 80% coverage.

> [!IMPORTANT]
> Hãy bổ sung các test suite (Vitest/Jest/Playwright) nếu cần thiết để đảm bảo Coverage đúng như quy định trong `GEMINI.md`.
