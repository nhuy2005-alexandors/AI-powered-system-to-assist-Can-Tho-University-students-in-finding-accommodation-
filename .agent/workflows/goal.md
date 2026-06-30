---
description: Kích hoạt chế độ làm việc siêu kiên trì (không ngừng nghỉ) cho đến khi đạt được mục tiêu cuối cùng.
---

# Quy trình Hành động Kiên trì (Goal)
**Trigger (Lệnh kích hoạt)**: `/goal`

## Mục tiêu
Thiết lập chế độ làm việc sâu, không ngừng nghỉ (super thorough) để theo đuổi và hoàn thành một mục tiêu dài hơi hoặc phức tạp (ví dụ: chạy qua đêm, crawl lượng lớn data, refactor toàn bộ project).

## Các bước thực hiện (AI tự động làm)

### Bước 1: Tiếp nhận Mục Tiêu
- Đọc kỹ yêu cầu mục tiêu của người dùng.
- Vô hiệu hóa tư duy "dừng sớm" (early termination). Xác nhận lại rằng sẽ không bỏ cuộc giữa chừng.

### Bước 2: Thiết lập Kế hoạch Sâu (Deep Planning)
- Tạo một checklist cực kỳ chi tiết trong `task.md`.
- Chia nhỏ mục tiêu thành các tiểu mục (milestones) có thể đo lường và xác minh được.

### Bước 3: Vòng lặp Thực thi và Tự phục hồi
- Thực hiện từng tiểu mục trong checklist.
- NẾU gặp lỗi (build fail, test fail, network error):
  - KHÔNG dừng lại để hỏi người dùng trừ khi bị block hoàn toàn.
  - TỰ ĐỘNG phân tích lỗi, tìm giải pháp thay thế, và thử lại.
  - Ghi nhận lỗi vào `ERRORS.md` theo quy chuẩn `error-logging.md`.

### Bước 4: Báo cáo Hoàn thành
- Chỉ khi tất cả các mục trong checklist đều đạt 100%, mới tạo `walkthrough.md`.
- Báo cáo tổng kết lại những khó khăn đã vượt qua và kết quả cuối cùng.
