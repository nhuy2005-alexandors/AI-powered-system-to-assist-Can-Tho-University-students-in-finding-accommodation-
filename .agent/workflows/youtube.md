---
description: [Nâng cao] Phân tích video YouTube (Tutorials), bóc tách các bước cài đặt công nghệ và tự động triển khai vào dự án.
---

# Quy trình Phân tích Video (YouTube to Action)
**Trigger (Lệnh kích hoạt)**: `/youtube [URL]`

## Mục tiêu
Tự động hóa quá trình học hỏi từ video hướng dẫn trên YouTube và áp dụng trực tiếp vào mã nguồn của người dùng.

## Các bước thực hiện
### Bước 1: Nhận URL và Nạp Kỹ năng
- Kích hoạt kỹ năng `.agent/skills/youtube-to-action/SKILL.md`.

### Bước 2: Kích hoạt Subagent
- Dùng `browser_subagent` để truy cập URL. Lệnh cho subagent: "Hãy truy cập video này. **Việc đầu tiên là nhấn phím 'k' để tạm dừng video hoặc bấm nút Mute để không phát âm thanh làm ồn người dùng**. Sau đó, tìm và đọc toàn bộ phần Transcript của video, nếu có đoạn code nào xuất hiện trên màn hình hoặc trong mô tả (Description), hãy trích xuất luôn".

### Bước 3: Lên Kế Hoạch (Plan)
- Dựa trên dữ liệu Subagent trả về, phân tích bài toán (Ví dụ: Video hướng dẫn cấu hình MCP).
- Đề xuất `implementation_plan.md` và xin phép người dùng.

### Bước 4: Thực Thi (Execution)
- Sau khi được Approve, làm theo đúng các bước trong video đã ánh xạ sang dự án.
- Cập nhật `walkthrough.md` khi hoàn tất.
