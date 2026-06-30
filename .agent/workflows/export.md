---
description: Tự động tổng hợp báo cáo và xuất dữ liệu ra file vật lý (Docs, CSV, PDF).
---

# Quy trình Xuất Dữ Liệu (Data Export)
**Trigger**: `/export`, `/report`

## Mục tiêu
Tự động hóa quá trình đóng gói dữ liệu trên IDE thành các file vật lý để người dùng dễ dàng sử dụng bên ngoài.

## Các bước thực hiện
1. Đọc và phân tích yêu cầu xuất dữ liệu của người dùng.
2. Load kỹ năng `data-exporter` từ `.agent/skills/data-exporter/SKILL.md`.
3. Thu thập dữ liệu cần thiết (từ lịch sử chat, từ JSON hoặc kết quả phân tích hệ thống).
4. Thực thi script (Python hoặc Node.js) để tạo file (ví dụ: `.docx`, `.csv`) lưu trực tiếp vào thư mục máy tính của người dùng.
