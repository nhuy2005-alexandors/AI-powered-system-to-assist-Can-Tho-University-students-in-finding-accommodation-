---
description: Hấp thụ nhanh nội dung từ một URL, lưu vào Obsidian và đề xuất áp dụng vào dự án.
---

# Quy trình Hấp thụ Dữ liệu Web (URL Absorb)
**Trigger (Lệnh kích hoạt)**: `/absorb [URL]`

## Mục tiêu
Tự động cào dữ liệu, trích xuất, đọc hiểu và tiêu hóa thông tin từ bất kỳ URL nào người dùng cung cấp (Bài báo, tài liệu API, hướng dẫn, GitHub Repo, v.v.).

## Các bước thực hiện (AI tự động làm)

### Bước 1: Phân loại và Thu thập Dữ liệu (URL Routing)
- **YouTube**: Nếu URL thuộc miền `youtube.com` hoặc `youtu.be`, KHÔNG dùng trình duyệt bình thường, bắt buộc bẻ lái sang chạy lệnh `/youtube` (kỹ năng `youtube-to-action`).
- **Trang web tĩnh**: Ưu tiên sử dụng công cụ `read_url_content` để quét nhanh nội dung HTML/Markdown (tốc độ dưới 2 giây).
- **Trang web động/Bị chặn**: Nếu tool quét tĩnh thất bại (do Cloudflare, yêu cầu JS, Captcha), bắt buộc chuyển sang dùng `browser_subagent` (Stealth Mode) để cào dữ liệu như một người dùng thực. Tuyệt đối không dừng lại hỏi ý kiến người dùng.
- **Quét sâu (Deep Crawling)**: Nếu URL được cấp là trang danh mục (Category) hoặc trang chủ (Homepage), AI có đặc quyền chủ động quét và trích xuất các đường link con (Sub-links) nổi bật bên trong trang đó. AI tự động gọi thêm công cụ `read_url_content` để truy cập các trang chi tiết nhằm thu thập dữ liệu sâu hơn, kéo mã nguồn hoặc quy chuẩn về thư viện mà không cần đợi lệnh từ người dùng.

### Bước 2: Tiêu hóa và Chắt lọc (Distillation)
AI tự động đọc hiểu và phân tích nội dung thu thập được:
- Trích xuất các ý chính (Key Takeaways).
- Cô đọng các đoạn mã quan trọng (Code Snippets) hoặc cú pháp lõi nếu đó là tài liệu công nghệ.

### Bước 3: Lưu trữ Vĩnh cửu (Obsidian Sync)
- Ngay sau khi đọc hiểu, AI phải tự động tạo một bản tóm tắt siêu tinh gọn (kèm link gốc) và lưu vào "Não bộ" tại: `Obsidian_Vault/Memory/Tech_Stack/`.
- Đảm bảo file được tạo có đúng chuẩn YAML Frontmatter (aliases, tags) và được gán link vào `200_Tech_Stack_MoC.md`.

### Bước 4: Ứng dụng Thực tiễn (Action Proposal)
- Trình bày một báo cáo ngắn gọn trên khung Chat về những gì vừa học được.
- **Quan trọng**: Bắt buộc phải đặt một câu hỏi cho người dùng: *"Tôi đã học xong kiến thức này và lưu vào bộ nhớ. Bạn có muốn tôi lập kế hoạch áp dụng đoạn code/kiến trúc từ link này vào dự án hiện tại của chúng ta không?"*
- Nếu người dùng đồng ý, AI sẽ chuyển sang quy trình `/plan` và `/create` để thực thi.
