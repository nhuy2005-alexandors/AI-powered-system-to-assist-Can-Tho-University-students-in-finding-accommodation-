---
description: Kích hoạt chế độ Daemon chạy ngầm, vô hiệu hóa tương tác người dùng và tự động phê duyệt để thực thi các tác vụ dài hạn.
---

# Quy trình Kích hoạt Daemon (Background Worker)
**Trigger (Lệnh kích hoạt)**: `/daemon`

## Mục tiêu
Biến AI thành một tiến trình chạy ngầm thực thụ (CLI-mode) để xử lý các tác vụ dài hạn mà không cần bất kỳ sự tương tác, hỏi han hay yêu cầu phê duyệt (Auto-Approve) từ người dùng. Mọi hành động được thực thi âm thầm, kết quả và lỗi được ghi ra file log.

## Các bước thực hiện (AI tự động làm)

### Bước 1: Tiếp nhận Lệnh & Tắt Tương Tác
- Xác nhận nhiệm vụ cần thực hiện ngầm từ người dùng (ví dụ: cào dữ liệu, audit code).
- Tự động thiết lập "Auto-Approve = true" trong suy nghĩ: Không tạo bảng hỏi ý kiến, không chờ duyệt kế hoạch.

### Bước 2: Kích hoạt Kỷ Luật Thép (Watchdog)
- Đọc bộ luật `.agent/rules/domain-daemon.md` để áp dụng chế độ tự quản.
- Nếu gặp lỗi trong quá trình thực thi, áp dụng ngay chiến thuật tự phục hồi (Self-Healing). Nếu thất bại 3 lần, ghi vào `ERRORS.md` và bỏ qua, TUYỆT ĐỐI không dừng lại hỏi người dùng.

### Bước 3: Thực thi Bất Đồng Bộ
- Sử dụng các công cụ `run_command`, `schedule` hoặc phân tách luồng để chạy ngầm.
- Triệt tiêu việc in ra các output lớn vào khung chat. Mọi output cần được chuyển hướng (redirect) vào file log hoặc lưu vào bộ nhớ Obsidian.

### Bước 4: Báo cáo Kết Thúc (Silent Output)
- Khi hoàn thành tác vụ, chỉ in ra một thông báo rất ngắn kèm theo đường dẫn file chứa kết quả (Ví dụ: "✅ Tác vụ chạy ngầm hoàn tất. Kết quả lưu tại `[daemon_report.md](...)`").
- Kích hoạt quy trình lưu trí nhớ `obsidian-memory-sync` nếu có tri thức mới cần lưu.
