---
name: Social Media Reach
description: Kỹ năng RAG siêu cấp giúp AI Agent vượt rào cản MXH (Reddit, Twitter, YouTube). Dùng Smart Routing và Sub-agent để cào dữ liệu khi API tĩnh thất bại.
---

# Kỹ năng: Social Media Reach (Truy xuất đa kênh)

## 1. Giới thiệu
Lấy cảm hứng từ kiến trúc `Agent-Reach`, kỹ năng này cấp cho bạn khả năng tiếp cận tri thức thời gian thực từ các nền tảng mạng xã hội thường hay chặn bot (như X/Twitter, Reddit, Bilibili, YouTube) mà không cần phụ thuộc vào API Key đắt đỏ.

## 2. Cơ chế Hoạt động (Mechanics)

Khi người dùng yêu cầu thu thập dữ liệu từ Mạng xã hội, hãy tuân thủ quy trình **Smart Routing**:

### Route 1: Bề mặt (Search Engine API)
- Sử dụng công cụ mặc định `search_web` hoặc `tavily-web` để tìm kiếm thông tin chung. 
- *Ưu điểm:* Nhanh, nhẹ. 
- *Nhược điểm:* Hay bị chặn bởi Reddit/Twitter.

### Route 2: Xâm nhập bằng Trình duyệt (Browser Subagent Fallback)
- Nếu Route 1 bị chặn hoặc dữ liệu không đủ sâu, BẮT BUỘC chuyển sang dùng công cụ `browser_subagent`.
- **Nhiệm vụ của Subagent:**
  - `Task`: "Mở trang web `[URL]`. Nếu gặp Captcha hoặc tường lửa, hãy cố gắng vượt qua bằng mô phỏng hành vi người dùng. Đọc tất cả các bình luận/bài viết hiển thị và xuất ra text."
  - `TaskName`: "Deep Scraping via Browser"

### Route 3: Doctor Mode (Tự chẩn đoán)
- Nếu Browser Subagent cũng thất bại (Ví dụ: Yêu cầu đăng nhập), AI phải báo cáo lại người dùng (Doctor Mode) bằng cách xuất ra một `walkthrough.md` lỗi.
- Gợi ý người dùng cung cấp Session Cookie cục bộ hoặc nhờ người dùng tự thao tác login qua UI của Agent.

## 3. Ứng dụng
- Phân tích xu hướng (Trending topics).
- Đọc bình luận (Sentiment analysis) thực tế từ người dùng để chốt ý tưởng làm SaaS.
- Đào sâu vào Github Issues của các dự án khác.
