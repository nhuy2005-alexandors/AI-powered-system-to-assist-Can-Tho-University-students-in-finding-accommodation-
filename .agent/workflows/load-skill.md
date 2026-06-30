---
description: Tự động tải kỹ năng từ Thư viện Ngoại vi (Skills_Library) vào vùng lõi để sử dụng.
---

# Quy trình Tải Kỹ năng Động (Dynamic Skill Loader)
**Trigger (Lệnh kích hoạt)**: `/load-skill`

## Mục tiêu
Cho phép AI tự động tìm kiếm và tải một kỹ năng cụ thể từ Thư viện Kỹ năng Ngoại vi (`Skills_Library`) vào vùng lõi (`.agent/skills/`) để sử dụng, nhằm tránh tình trạng quá tải Token (Context Bloat).

## Các bước thực hiện (AI tự động làm)

### Bước 1: Phân tích Yêu cầu
- Đọc kỹ tên kỹ năng người dùng muốn tải (Ví dụ: `/load-skill react-patterns`).

### Bước 2: Tìm kiếm Kỹ năng trong Thư viện
- Sử dụng lệnh Terminal (PowerShell) để kiểm tra xem kỹ năng đó có tồn tại trong `Skills_Library` hay không.
- Nếu không nhớ chính xác tên, AI phải tự tìm kiếm gần đúng (fuzzy search) trong thư mục đó.

### Bước 3: Di chuyển Kỹ năng
- Sao chép (Copy) thư mục kỹ năng từ `Skills_Library` vào `.agent/skills/`.
- Thông báo cho người dùng kỹ năng đã được kích hoạt thành công.
- Lưu ý: AI có thể tự động sao chép skill khi nhận diện tác vụ cần thiết mà không đợi người dùng gõ lệnh `/load-skill`, tuy nhiên phải báo cáo lại.
