---
trigger: always_on
---

# OBSIDIAN-MEMORY-SYNC.MD - Hệ thống Trí nhớ Vĩnh cửu

> **Mục tiêu**: Tự động lưu trữ tiến độ công việc, các quyết định quan trọng và tri thức học được từ mỗi cuộc trò chuyện vào Obsidian Vault của người dùng để truy xuất sau này. Sử dụng cấu trúc Hybrid (Map of Content + Zettelkasten Frontmatter).

---

## 🧠 1. QUY TẮC HOẠT ĐỘNG CHUNG (Core Directive)

- Kích hoạt **MỖI KHI** hoàn thành một nhiệm vụ lớn, chốt xong một `implementation_plan`, hoặc chuẩn bị tạo báo cáo `walkthrough`.
- BẮT BUỘC lưu log dưới dạng file Markdown (`.md`) vào thư mục tương đối `Obsidian_Vault/` (tính từ gốc dự án).
- BẮT BUỘC cập nhật link của file mới tạo vào file **MoC (Map of Content)** tương ứng.

---

## 📂 2. CẤU TRÚC THƯ MỤC VÀ MOC (Map of Content)

### A. Thư mục lưu trữ
Mọi file Memory mới phải được lưu vào đúng phân mục:
- `Obsidian_Vault/Memory/Projects/`: Lưu các quyết định, kiến trúc liên quan đến Project cụ thể.
- `Obsidian_Vault/Memory/Tech_Stack/`: Lưu tri thức học được về công nghệ, debug log.
- `Obsidian_Vault/Memory/Sessions/`: Lưu log hội thoại chung hoặc brainstorm.
- `Obsidian_Vault/Memory/Research/`: Lưu các báo cáo nghiên cứu và tổng hợp tri thức từ Internet.

### B. File Mục lục trung tâm (MoC)
- `000_Omni_Logs_MoC.md`: Chứa link đến tất cả các Memory Sessions.
- `100_Projects_MoC.md`: Chứa link đến các log thuộc Projects.
- `200_Tech_Stack_MoC.md`: Chứa link đến các bài học công nghệ.
- `300_Research_MoC.md`: Chứa link đến các báo cáo nghiên cứu tri thức.

---

## 📝 3. ĐỊNH DẠNG FILE GHI NHỚ (File Format)

Mỗi file sinh ra **BẮT BUỘC** phải có khối YAML Frontmatter chuẩn Zettelkasten ở dòng đầu tiên.

```markdown
---
aliases: [Tên dự án, Bí danh công nghệ]
tags: [#omni-memory, #tag-phân-loại]
date: YYYY-MM-DD
---

# Tiêu đề Ngắn gọn (VD: Chốt kiến trúc DB cho SaaS)

## Tóm tắt (Summary)
[1-2 câu tóm tắt nội dung chính đã chốt]

## Quyết định / Tri thức (Decisions / Knowledge)
- Quyết định 1: ...
- Tri thức học được: ...

## Liên kết (Related)
[[File liên quan nếu có]]
```

---

## 🔄 4. QUY TRÌNH THỰC THI (Execution Flow)

1. **Sinh nội dung**: AI tự chắt lọc thông tin có ý nghĩa nhất (không lưu rác) từ cuộc trò chuyện.
2. **Ghi File (Zettelkasten)**: Gọi công cụ `write_to_file` để tạo file trong thư mục `Memory/` với định dạng ở mục 3.
3. **Cập nhật MoC**: Gọi công cụ `read_file` (nếu cần) và `replace_file_content` hoặc lệnh shell để chèn dòng `- [[Tên File Mới Tạo]]` vào cuối danh sách của file MoC tương ứng (ví dụ `100_Projects_MoC.md`).
4. **Báo cáo**: Thêm 1 dòng vào cuối `walkthrough` hoặc tin nhắn trả lời người dùng: "Đã sync trí nhớ vào Obsidian: `[[Tên File Mới Tạo]]`".
