---
description: Đặt lịch chạy định kỳ hoặc đếm ngược thời gian cho một tác vụ cụ thể.
---

# Quy trình Lập lịch và Chờ đợi (Schedule)
**Trigger (Lệnh kích hoạt)**: `/schedule`

## Mục tiêu
Thiết lập một lịch trình chạy định kỳ (cron job) hoặc một bộ đếm thời gian (timer) một lần để thực thi các chỉ thị của người dùng vào một thời điểm trong tương lai.

## Các bước thực hiện (AI tự động làm)

### Bước 1: Thu thập Yêu cầu Thời gian
- Hỏi rõ người dùng về:
  - Loại lịch: Chạy một lần (Timer) hay lặp lại định kỳ (Cron)?
  - Cú pháp: Cần bao nhiêu giây (cho Timer) hoặc biểu thức Cron (cho Cron job)?
  - Tác vụ: Hệ thống cần làm gì khi đến giờ?

### Bước 2: Thiết lập Bộ đếm
- Sử dụng Tool `schedule` của hệ thống để thiết lập.
  - NẾU là Timer: Sử dụng `DurationSeconds` và `Prompt`.
  - NẾU là Cron: Sử dụng `CronExpression` và `Prompt`.

### Bước 3: Đợi tín hiệu và Phản ứng
- Thông báo cho người dùng biết lịch đã được thiết lập.
- Kết thúc lượt phản hồi để hệ thống đi vào trạng thái chờ (Idle/Wait).
- Khi có tín hiệu (notification) từ bộ đếm, tự động thức dậy và thực hiện tác vụ được mô tả trong `Prompt` của tín hiệu đó.
