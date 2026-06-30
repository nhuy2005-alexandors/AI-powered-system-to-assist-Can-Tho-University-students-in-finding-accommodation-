---
description: Thực hiện tra cứu nhanh (Quick Lookup) trên Internet để trả lời ngay lập tức các câu hỏi thực tế (Tỷ giá, thời tiết, phiên bản).
---

# Quy trình Tra cứu Nhanh (Quick Lookup)
**Trigger (Lệnh kích hoạt)**: `/ask`, `/web`, `/lookup`, `/quick`

## Mục tiêu
Cung cấp một giải pháp "nhẹ và nhanh" (Lightweight Workflow) thay thế cho lệnh `/research` cồng kềnh, chuyên dùng để trả lời các câu hỏi đóng, cần đáp án ngay lập tức từ thực tế (Ground Truth) thay vì lấy từ dữ liệu huấn luyện (Training Data).

## Nguyên tắc Cốt lõi
- **Không sinh Artifact**: KHÔNG tạo file `.md` mới.
- **Không lưu Obsidian**: KHÔNG kích hoạt quy trình `obsidian-memory-sync`.
- **Tốc độ tối đa**: Trả lời ngay trong khung chat bằng 1-2 câu ngắn gọn.

## Các bước thực hiện (AI tự động làm)

### Bước 1: Kích hoạt Công cụ Tìm Kiếm
- Gọi ngay công cụ `search_web` với từ khóa được trích xuất từ câu hỏi của người dùng.
- Ưu tiên các query đơn giản, đánh thẳng vào mục tiêu (Ví dụ: "Tỷ giá Vietcombank USD hôm nay", "Claude 3.5 release date").

### Bước 2: Phân tích Nhanh (Snippet Reading)
- Đọc lướt qua phần mô tả ngắn (snippets) do kết quả tìm kiếm trả về. 
- Nếu snippet đã chứa đủ thông tin (như con số tỷ giá), DỪNG việc tìm kiếm sâu thêm. Không cần gọi `read_url_content` trừ khi thông tin bị che khuất.

### Bước 3: Phản hồi Trực tiếp (Direct Answer)
- Trả lời người dùng trực tiếp trong khung chat.
- Cấu trúc phản hồi:
  1. Câu trả lời trọng tâm (Con số, ngày tháng, sự kiện).
  2. Nguồn (1-2 Link URL gốc dạng `[Tên báo](URL)` để người dùng tự kiểm chứng).

> Mẫu: "Tỷ giá USD tại Vietcombank hôm nay (14/06/2026) là **25.450 VND**. Nguồn: [Vietcombank](https://...)"
