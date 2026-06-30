---
description: [Domain Thực Thi] Kích hoạt chế độ Freelancer tự động, tự mò mẫm và làm các "gig" độc lập qua MCP.
---

# Quy trình Thực thi Nhiệm vụ (Gig Execution)
**Trigger (Lệnh kích hoạt)**: `/task`

## Mục tiêu
Chuyển hóa AI thành một Freelancer làm gig, tự động nhận một yêu cầu lớn và tự mò mẫm cách hoàn thành trên máy hoặc trên Internet bằng các MCP Server (như GitHub, Vercel, Slack).

## Các bước thực hiện
### Bước 1: Phân tích Nhiệm vụ
- Tiếp nhận yêu cầu (Ví dụ: "Hãy vào Github clone repo này về, xem lỗi đang bị là gì và commit bản sửa lỗi").
- Kiểm tra tính khả thi và liệt kê các MCP Tools cần sử dụng.

### Bước 2: Tự Chủ (Autonomous Mode)
- Ở chế độ này, AI không chờ đợi người dùng nhúng tay. Nó tự động gọi `ask_permission` (nếu cần), tự động gọi các tool MCP liên tục.
- Nếu gặp lỗi (Bug), AI không báo cáo ngay mà tự động dùng `search_web` hoặc tool debug để sửa lỗi.

### Bước 3: Bàn giao (Delivery)
- Sau khi nhiệm vụ hoàn thành (Ví dụ: Đã push code lên nhánh mới), AI tạo ra một file báo cáo `walkthrough.md` liệt kê các thao tác đã làm để "Nghiệm thu" với người dùng.
