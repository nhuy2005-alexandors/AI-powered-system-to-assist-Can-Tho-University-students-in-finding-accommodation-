# 🌐 Quy Tắc Tương Tác Internet & Trình Duyệt (Web Ruleset)

Hệ thống được cấp quyền chủ động kết nối Internet và tương tác Trình duyệt (Browser) để phục vụ dự án. Tuy nhiên, mọi hành vi phải tuân thủ các quy định khắt khe sau:

## 1. Internet-First Grounding (Bắt buộc)
- **Ưu tiên Internet thay vì Dữ liệu Huấn Luyện**: Bất kỳ khi nào người dùng hỏi về thông tin công nghệ mới (sau 2023), lỗi bug chưa rõ nguyên nhân, cách dùng một thư viện phiên bản mới, hoặc cần kiến thức chuyên sâu, AI **BẮT BUỘC** phải gọi công cụ `search_web` hoặc `read_url_content` để lấy thông tin thực tế.
- **Chống Ảo Giác (Zero-Hallucination)**: Không được đoán mò hoặc chỉ dựa vào dữ liệu huấn luyện (Training Data) khi xử lý các task quan trọng. Việc dùng Training Data chỉ là kiến thức nền tảng, Internet Data mới là nguồn chân lý (Ground Truth).

## 2. Tìm kiếm Internet (`search_web` & `read_url_content`)
- **Phạm vi cho phép**: Được phép sử dụng Google Search để tìm kiếm tài liệu chuyên ngành, kiểm tra lỗi code (StackOverflow, GitHub Issues), cập nhật thư viện mới.
- **Tính xác thực (Fact-Checking)**: Đối với nội dung NCKH, chỉ ưu tiên cào dữ liệu từ các nguồn uy tín (`.edu`, `.gov`, `.org`, Google Scholar, PubMed). CẤM lấy số liệu từ các bài blog cá nhân thiếu kiểm chứng.
- **Bắt buộc Trích dẫn**: Mọi thông tin (số liệu, khái niệm) lấy từ Internet phải được đính kèm URL gốc ở mục Nguồn tham khảo.

## 2. Mô phỏng Trình duyệt (`browser_subagent`)
- **Mục đích sử dụng**: Sử dụng Subagent để mở UI trang web, kiểm tra responsive, tương tác form (Login, Đăng ký) và trích xuất báo cáo lỗi UI.
- **Giới hạn hành vi**: Không sử dụng Subagent để thu thập/cào dữ liệu hàng loạt (Scraping) vì gây tốn tài nguyên máy tính. Thay vào đó hãy dùng `read_url_content` nếu chỉ cần đọc chữ.
- **Báo cáo bằng Hình ảnh**: Mọi tác vụ do Browser Subagent thực hiện PHẢI trả về ảnh chụp màn hình (Screenshot) hoặc Video (WebP) để người dùng nghiệm thu.

## 3. Cách thức Tự động Hóa
Khi sinh viên gặp bế tắc về một vấn đề chưa có trong Codebase (Ví dụ: "Hãy tìm hiểu cách thuật toán ghép cặp phòng trọ hoạt động"), AI được quyền **tự động** chạy `search_web` mà không cần xin phép, miễn là nó phục vụ mục đích phá vỡ bế tắc.
