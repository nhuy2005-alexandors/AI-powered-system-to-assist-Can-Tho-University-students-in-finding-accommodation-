---
description: Kích hoạt quy trình Meta-Config, AI tự động review và nâng cấp luật cấu hình của chính nó dựa trên yêu cầu mới.
---

# Quy trình Tự Cấu Hình Hệ Thống (Meta-Config)
**Trigger (Lệnh kích hoạt)**: `/config`, `/upgrade`, `/meta`

## Mục tiêu
Cho phép AI tự động review và cập nhật lại chính Template của nó dựa trên sự thay đổi về định hướng của dự án (Context Shift).

## Các bước thực hiện (AI tự động làm)

### Bước 1: Tiếp nhận và Phân tích Yêu cầu
- Đọc kỹ định hướng mới của người dùng (Ví dụ: "Hệ thống không làm NCKH nữa, chuyển sang làm SaaS kiếm tiền").
- Load kỹ năng `template-architect` từ `.agent/skills/template-architect/SKILL.md`.
- **Nghiên cứu Thị trường (Internet Research Bắt buộc)**: Trước khi chốt bất kỳ giải pháp thiết kế nào cho tính năng mới, AI phải thực hiện tra cứu Internet (tìm kiếm xu hướng, các kho lưu trữ Github nổi bật, Best Practices) về tính năng đó.
- **Deep Learning Over Speed**: Trước khi đề xuất Meta-Config tích hợp một công nghệ/kỹ năng mới, AI BẮT BUỘC phải đọc sâu vào mã nguồn hoặc cấu trúc (như `sub-skills/`) của công nghệ đó để thấu hiểu cơ chế hoạt động thực tế.
- **Suy ngẫm & Chắt lọc**: Tổng hợp thông tin từ Internet và đối chiếu với cấu trúc hiện tại của hệ thống để đưa ra phương án tối ưu nhất.

### Bước 2: Rà soát Cấu trúc Hiện tại
- Mở và đọc `GEMINI.md` để phân tích danh tính (Identity) hiện tại.
- Đọc các luật liên quan trong `.agent/rules/` (như `ACADEMIC.md`, `third-party-integration.md`) để tìm điểm mâu thuẫn.

### Bước 3: Lập kế hoạch (Implementation Plan)
- Tạo file `implementation_plan.md` liệt kê chi tiết:
  - Cần đổi Danh tính (Identity) trong `GEMINI.md` thành gì?
  - Cần vô hiệu hóa hoặc sửa file luật nào?
  - Xin phép người dùng để tiến hành "Lột xác" (Metamorphosis).

### Bước 4: Thực thi và Báo cáo
- Tiến hành ghi đè/chỉnh sửa các file cấu hình.
- Sinh ra `walkthrough.md` thông báo hệ thống đã được tái sinh (Reborn) với cấu hình mới, sẵn sàng nhận lệnh tiếp theo.
