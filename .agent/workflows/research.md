---
description: Thực hiện tìm kiếm chuyên sâu trên Internet, tổng hợp tri thức mới và lưu trữ vào Obsidian.
---

# Quy trình Nghiên cứu Chuyên sâu (Research Engine)
**Trigger (Lệnh kích hoạt)**: `/research`

## Mục tiêu
Biến AI thành một cỗ máy nghiên cứu không mệt mỏi. Ra ngoài Internet thu thập, đối chiếu dữ liệu, và chắt lọc thành tri thức hữu ích để báo cáo cho người dùng và tự động lưu trữ vĩnh viễn vào hệ thống Second Brain.

## Cấu trúc Báo cáo (Report Format)
Mọi báo cáo sinh ra từ lệnh này phải tuân thủ nghiêm ngặt 2 phần:
1. **Nhanh gọn thực tiễn (Key-Takeaways)**: Những ý chính, tóm tắt siêu ngắn gọn có thể áp dụng ngay.
2. **Học thuật chuyên sâu (Deep-dive & Citations)**: Trích dẫn rõ ràng các luận điểm, kèm theo URL/Nguồn để đối chiếu (tránh ảo giác - hallucination).

## Các bước thực hiện (AI tự động làm)

### Bước 1: Trích xuất & Phân rã Từ khóa (Query Decomposition)
- AI không search toàn bộ câu hỏi. AI phải bóc tách câu hỏi thành 2-3 câu truy vấn (queries) nhỏ, độc lập để đào sâu nhiều góc độ.
- Load kỹ năng tìm kiếm (Ví dụ: `tavily-web`, `exa-search`, hoặc dùng tool mặc định `search_web`).

### Bước 2: Truy xuất & Đối chiếu (Multi-Thread Retrieval)
- **Deep Learning Over Speed (Truy cập thông tin triệt để)**: Mọi công nghệ mới bắt buộc phải được đào sâu tận lõi mã nguồn hoặc tài liệu chi tiết (như `src/`, `sub-skills/`). KHÔNG được đưa ra kết luận nếu chỉ mới xem mô tả bề mặt ở README.
- Sử dụng công cụ Search web để lấy thông tin.
- Nếu gặp bài viết chất lượng cao, dùng `read_url_content` hoặc `browser_subagent` để đọc toàn văn.
- Đối chiếu chéo thông tin giữa các nguồn để đảm bảo độ tin cậy.

### Bước 3: Tổng hợp Báo cáo (Synthesis & Artifact)
- AI tạo ra một Artifact (`research_report.md` hoặc tên tùy chỉnh) để trình bày kết quả theo cấu trúc quy định ở trên (Takeaways + Deep-dive).
- Artifact phải sử dụng định dạng Markdown đẹp, có bảng so sánh nếu cần.

### Bước 4: Lưu trữ Vĩnh Cửu (Obsidian Memory Sync)
- Ngay sau khi chốt báo cáo, AI BẮT BUỘC phải thực hiện quy trình `obsidian-memory-sync`:
  - Trích xuất 1 bản tóm tắt cực ngắn gọn kèm link tới báo cáo đầy đủ (hoặc lưu thẳng toàn văn nếu cần).
  - Ghi vào thư mục `Obsidian_Vault/Memory/Research/`.
  - Sinh YAML Frontmatter (`aliases`, `tags`).
  - Mở file `300_Research_MoC.md` và chèn link `[[Tên File Báo Cáo]]` vào danh mục.
