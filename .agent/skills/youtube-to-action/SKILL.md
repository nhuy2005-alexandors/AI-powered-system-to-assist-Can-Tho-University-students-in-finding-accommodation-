---
name: YouTube to Action
description: Kỹ năng hấp thụ tri thức từ video YouTube (như video hướng dẫn code, setup phần mềm) bằng cách dùng subagent đọc transcript và chuyển hóa thành Kế hoạch triển khai (Implementation Plan) cho dự án hiện tại.
---

# Kỹ năng: YouTube-to-Action (Phân tích Video Công nghệ)

## 1. Giới thiệu
Kỹ năng này biến bạn thành một người học hỏi chủ động. Khi người dùng cung cấp một URL YouTube về hướng dẫn (Tutorial) hoặc tích hợp công nghệ (Ví dụ: Tích hợp Obsidian với Antigravity IDE), nhiệm vụ của bạn là "xem" video đó, hiểu các bước, và chuẩn bị áp dụng vào dự án của người dùng.

## 2. Quy trình "Hấp thụ" (Assimilation Protocol)

### Bước 1: Trích xuất Dữ liệu (Extraction)
- Video YouTube không thể xem bằng mắt. Bạn PHẢI sử dụng công cụ `browser_subagent` (hoặc `read_url_content` nếu khả thi) để truy cập trang web YouTube của video đó.
- **[QUAN TRỌNG - CHỐNG ỒN]:** Ngay trong câu lệnh Task gửi cho `browser_subagent`, bạn PHẢI dặn nó: *"Vào trang cái là bấm Pause (tạm dừng) video hoặc Mute (tắt tiếng) ngay lập tức để không phát ra âm thanh ồn ào"*.
- Yêu cầu `browser_subagent` mở phần **Transcript (Bản ghi lời thoại)** hoặc dùng công cụ tìm kiếm web (`search_web`) để tìm bản text tóm tắt của video nếu không đọc được transcript trực tiếp.

### Bước 2: Giải mã & Rút trích (Decoding)
- Sau khi có transcript/thông tin video, phân tích để tìm ra:
  1. Mục tiêu của video là gì?
  2. Các công nghệ/công cụ được sử dụng.
  3. **Các bước (Step-by-step)** mà tác giả hướng dẫn.

### Bước 3: Lập Bản đồ Áp dụng (Implementation Mapping)
- Tuyệt đối không nhắm mắt code luôn. Bạn phải đối chiếu các bước trong video với **cấu trúc dự án hiện tại** của người dùng.
- Viết ra một `implementation_plan.md` trình bày rõ: Lấy được gì từ video và sẽ code vào những file nào. 
- **Tự động thực thi (Auto-execute)**: Sau khi lập xong `implementation_plan.md`, AI có toàn quyền tự động tiến hành viết/sửa code để áp dụng kiến thức vào dự án luôn mà KHÔNG CẦN dừng lại chờ người dùng duyệt.

> **Ghi chú tự động hóa**: AI phải tự động chạy một mạch từ Bước 1 (Trích xuất) đến Bước 3 (Áp dụng code) mà **KHÔNG ĐƯỢC** dừng lại hỏi ý kiến người dùng bất cứ lúc nào để tối đa hóa tốc độ.
