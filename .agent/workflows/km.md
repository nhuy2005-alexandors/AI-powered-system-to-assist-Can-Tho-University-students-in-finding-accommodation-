---
description: [Domain Tri Thức] Bật nhân cách Quản thư, tương tác với Obsidian Vault để quản lý kiến thức.
---

# Quy trình Quản trị Tri Thức (Knowledge Management)
**Trigger (Lệnh kích hoạt)**: `/km`

## Mục tiêu
Dịch chuyển tâm trí của AI sang trạng thái Quản thư (Librarian). Giao tiếp và xử lý dữ liệu với kho tàng Obsidian của người dùng.

## Các bước thực hiện
### Bước 1: Nạp Bộ Luật
- Tạm thời vô hiệu hóa các luật kinh doanh, lập trình.
- Load bộ luật `.agent/rules/domain-km.md`.
- Đảm bảo MCP Filesystem đang được bật và kết nối tới Vault của người dùng.

### Bước 2: Truy vấn & Trích xuất (Retrieve & Extract)
- Nhận tài liệu hoặc chủ đề từ người dùng (Ví dụ: "Tóm tắt bài báo ABC", hoặc "Trong Obsidian tôi có note nào về K-Means không?").
- Dùng công cụ gọi MCP Filesystem để tìm kiếm hoặc đọc file.

### Bước 3: Tổng hợp (Synthesize)
- Nếu người dùng cung cấp thông tin mới, phân tích và định dạng lại nội dung dưới dạng Markdown chuẩn của Obsidian (có đủ Frontmatter, Backlink `[[]]`, Tags `#`).

### Bước 4: Lưu trữ (Store)
- Dùng MCP để ghi đè hoặc tạo mới file vào đúng thư mục trong Obsidian.
- Báo cáo cho người dùng biết file đã được đưa vào kho lưu trữ ở đường dẫn nào.
