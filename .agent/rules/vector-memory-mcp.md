# VECTOR-MEMORY-MCP.MD - Hệ thống Trí nhớ Vĩnh cửu Vector

> **Mục tiêu**: Sử dụng Model Context Protocol (MCP) và Vector Database (LanceDB) để thay thế khả năng ghi nhớ tuyến tính, cho phép AI chủ động tìm kiếm và khôi phục ngữ cảnh (Context Restoration) từ quá khứ.

---

## 🧠 1. KHI NÀO SỬ DỤNG VECTOR MEMORY

Hệ thống được chỉ định tự động sử dụng Vector Memory trong các trường hợp sau:
1. **Khởi đầu phiên làm việc mới**: Khi người dùng hỏi một câu liên quan đến dự án cũ hoặc lỗi cũ mà AI không có trong context window.
2. **Khi gặp bug lặp lại**: Trước khi debug, AI phải truy vấn Vector DB xem lỗi này đã từng xảy ra chưa.
3. **Khi cần tham chiếu Coding Standards**: Lấy ra các chuẩn mực code đã thống nhất trước đó.

## 🔄 2. QUY TRÌNH "REMEMBERING" (Khôi phục trí nhớ)

Thay vì đoán mò, AI PHẢI thực hiện quy trình sau:
1. **Search (Tìm kiếm)**: Sử dụng công cụ tương tác với `agent-memory-mcp` (thông qua lệnh gọi MCP Server) để truy vấn từ khóa (Ví dụ: "Lỗi kết nối MongoDB tuần trước").
2. **Inject (Nhúng ngữ cảnh)**: Đọc các kết quả Vector Search (có độ tương đồng cao) và dùng nó làm cơ sở để trả lời.

## 📥 3. QUY TRÌNH "MEMORIZING" (Ghi nhớ kiến thức mới)

Mỗi khi giải quyết xong một bug khó, hoặc chốt xong một thiết kế kiến trúc quan trọng:
- AI **BẮT BUỘC** phải gọi lệnh lưu trữ của `agent-memory-mcp` để đẩy đoạn tri thức này vào LanceDB.
- Định dạng lưu trữ: `[Tên Project] - [Loại (Bug/Design)] - [Nội dung tóm tắt]`.
