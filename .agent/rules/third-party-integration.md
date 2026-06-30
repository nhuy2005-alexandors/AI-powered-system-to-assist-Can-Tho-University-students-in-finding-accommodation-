# 🔗 Quy Tắc Tích Hợp Bên Thứ 3 qua MCP (Model Context Protocol)

Hệ thống bắt buộc phải sử dụng giao thức **MCP (Model Context Protocol)** khi cần tương tác với bất kỳ nền tảng bên ngoài nào (GitHub, Google Drive, Vercel, Database từ xa, v.v.) nhằm đảm bảo tính bảo mật và chuẩn hóa dữ liệu.

## 1. Nguyên Tắc "MCP-First"
- Trước khi thực hiện bất kỳ lệnh terminal thô (như `git clone`, `git push` hay `curl` gọi API), AI **PHẢI** kiểm tra xem có MCP Server nào đang chạy cung cấp công cụ tương ứng hay không.
- Nếu có MCP Tool, ưu tiên sử dụng MCP Tool thay vì tự viết mã kịch bản (scripting).

## 2. Quản Lý Quyền Truy Cập (Permissions)
- Hệ thống Antigravity IDE giới hạn quyền truy cập MCP của AI. Để gọi một MCP Tool, AI phải có quyền (permission) được cấp bởi người dùng.
- Khi gọi Tool thất bại do thiếu quyền, AI phải tự động kích hoạt công cụ `ask_permission` với cấu trúc chuẩn sau:
  - `Action="mcp"`
  - `Target="tên_mcp_server/*"` (Ví dụ: `github/*` để xin quyền tất cả công cụ của server GitHub).
- **CẤM** xin quyền lẻ tẻ từng Tool một để tránh làm phiền người dùng. Xin quyền cấp Server.

## 3. Bảo Mật Thông Tin (Credentials)
- Tuyệt đối **CẤM** yêu cầu người dùng dán (paste) API Key, Access Token, mật khẩu vào khung chat. 
- Mọi thông tin nhạy cảm phải được cài đặt ngầm vào biến môi trường (`.env`) hoặc tệp cấu hình của MCP Server (như `mcp.json`).
- Không in Token hay khóa bí mật ra màn hình chat dưới mọi hình thức, kể cả khi in log lỗi.

## 4. Báo Cáo Kết Quả
- Dữ liệu trả về từ MCP Server thường có định dạng JSON. AI có trách nhiệm trích xuất thông tin trọng tâm và báo cáo lại bằng văn bản tự nhiên, không in nguyên cục JSON rác lên giao diện người dùng.
