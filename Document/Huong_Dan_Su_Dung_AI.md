# 📚 Hướng Dẫn Sử Dụng Hệ Thống AI Master Kit (Dự án NCKH)

Tài liệu này hướng dẫn cách tương tác hiệu quả nhất với bộ template "Vibe Coding" (gồm 15 AI Agents và 573 Kỹ năng) để xây dựng đề tài Nghiên cứu Khoa học.

---

## 1. Cơ Chế Hoạt Động Cốt Lõi
Hệ thống này **không phải** là một Chatbot thông thường. Nó là một đội ngũ kỹ sư ảo.
* Thay vì "nhớ" mọi thứ, nó sẽ tự động tải các **Kỹ năng (Skills)** từ thư mục `NCKH/.agent/skills/` ra để đọc khi cần thiết.
* Thay vì ôm đồm mọi việc, nó sẽ chuyển đổi giữa các **Vai trò (Agents)** (như Architect, Engineer, QA) tùy theo giai đoạn của dự án.

---

## 2. Cách Sử Dụng Lệnh Nhanh (Slash Commands)
Gõ trực tiếp các lệnh này (ví dụ: `/brainstorm ý tưởng NCKH`) vào khung chat để hệ thống tự động tải Workflow làm việc tương ứng:

* 🔌 **`/api`**: Thiết kế và tạo tài liệu API theo chuẩn OpenAPI 3.1.
* 📋 **`/audit`**: Kiểm tra lại toàn diện hệ thống theo chuẩn Auditor trước khi bàn giao.
* ✍️ **`/blog`**: Tự động tạo hệ thống viết blog cá nhân hoặc doanh nghiệp.
* 🧠 **`/brainstorm`**: Bí ý tưởng? Yêu cầu AI gợi ý và phản biện theo chuẩn Senior.
* ⚖️ **`/compliance`**: Kiểm tra tính tuân thủ pháp lý và dữ liệu (GDPR, HIPAA, SOC2).
* 🚀 **`/create`**: Muốn tạo tính năng mới từ A-Z? AI sẽ tự động phân tích, viết code và kiểm thử.
* 🐛 **`/debug`**: Gặp lỗi khó sửa? AI sẽ soi log và truy vết nguyên nhân gốc rễ.
* 🚢 **`/deploy`**: Tự động đóng gói và đẩy code lên Server/Vercel.
* 📄 **`/document`**: Tự động viết tài liệu dự án chuyên nghiệp.
* 🎨 **`/enhance`**: Sửa màu, thêm nút, tinh chỉnh logic nhỏ lẻ.
* 🎓 **`/explain`**: Giải thích code chuyên sâu và chuyển giao kiến thức.
* 🎯 **`/goal`** *(Lệnh hệ thống)*: Ép AI làm việc liên tục đến khi đạt mục tiêu lớn (bỏ qua gián đoạn).
* 📝 **`/log-error`**: Ghi lại lỗi vào Error Log để hệ thống học tập.
* 📱 **`/mobile`**: Tối ưu và phát triển ứng dụng Mobile (Native).
* 👁️ **`/monitor`**: Cài đặt giám sát hệ thống Server và Pipeline.
* 🤝 **`/onboard`**: Tự động đào tạo (Onboarding) thành viên mới trong team.
* 🎩 **`/orchestrate`**: Gọi hội đồng đa chuyên gia xử lý các task cực kỳ phức tạp.
* ⚡ **`/performance`**: Tối ưu tốc độ web theo chuẩn Performance Expert.
* 📅 **`/plan`**: Lập kế hoạch chi tiết cho dự án từ con số 0.
* 🎬 **`/preview`**: Khởi chạy chế độ xem trước (Preview) sản phẩm.
* ⏱️ **`/realtime`**: Tích hợp các tính năng thời gian thực (Socket.io, WebRTC).
* 🔄 **`/release-version`**: Cập nhật phiên bản mới và đồng bộ lại tài liệu.
* 🛡️ **`/security`**: Quét lỗ hổng và bảo mật dự án theo chuẩn Security Senior.
* 🔍 **`/seo`**: Tối ưu hóa SEO và GEO để lên top tìm kiếm.
* 📊 **`/status`**: Báo cáo tiến độ dự án bằng Dashboard chuyên nghiệp.
* 🧪 **`/test`**: Tự động viết test theo quy trình chuẩn TDD Master.
* 💎 **`/ui-ux-pro-max`**: Thiết kế giao diện Visuals Premium, hiện đại.
* 📚 **`/update-docs`**: Cập nhật lại tài liệu kỹ thuật khi có thay đổi.
* 🆙 **`/update`**: Kiểm tra và cập nhật phiên bản IDE.
* 🗺️ **`/visually`**: Biến đổi logic/kiến trúc phức tạp thành sơ đồ trực quan.
* 🎥 **`/youtube`**: [Nâng cao] Nhập URL video YouTube hướng dẫn để AI xem transcript và tự động code theo.
* ⚙️ **`/config`**: Trình quản trị hệ thống. Giúp bạn cấu hình lại hoặc nâng cấp AI theo ý muốn.

### 2.2 Các Trụ Cột Đa Lĩnh Vực (Domain Routing)
* 💼 **`/saas`**: Kích hoạt tư duy Khởi nghiệp/Sản phẩm kiếm tiền.
* 🎓 **`/nckh` / `/train`**: Kích hoạt tư duy Nghiên cứu Học thuật & Khoa học dữ liệu (Data Science).
* 🧠 **`/km`**: Kích hoạt tư duy Quản thư, tương tác đọc/ghi vào Obsidian.
* ⚡ **`/task`**: Kích hoạt chế độ Gig Worker tự động nhận và giải quyết lỗi bằng MCP.
---

## 3. Bí Kíp Tương Tác Hiệu Quả Cao (Prompt Engineering)

Để khai thác 100% công lực của hệ thống, hãy áp dụng công thức sau khi ra lệnh:

### Mẹo 1: Khai báo rõ vai trò & kỹ năng cần dùng
Thay vì nói: *"Làm cho tôi giao diện đăng nhập"*.
👉 **Nên nói:** *"Sử dụng kỹ năng `ui-ux-pro-max` và `react-best-practices`. Hãy thiết kế giao diện đăng nhập cực kỳ hiện đại, có Dark Mode."*

### Mẹo 2: Cung cấp Bối cảnh (Context) tuyệt đối
Thay vì nói: *"Sửa lỗi file này đi"*.
👉 **Nên nói:** *"Đọc file `app_build/src/app/login/page.tsx` và sửa lỗi Hydration ở dòng số 12 giúp tôi."*

### Mẹo 3: Áp dụng phương pháp "Checkpoint" (Đi từng bước)
Đừng bắt AI vừa thiết kế Data vừa code Frontend trong 1 câu lệnh. Nó sẽ bị "ngộp" và làm ẩu.
* **Bước 1:** *"Phân tích nghiệp vụ và thiết kế Database cho tính năng X. Lưu thành file `Spec.md`."*
* **Bước 2 (Sau khi duyệt):** *"Đọc file `Spec.md` và bắt đầu viết API Backend cho tôi."*
* **Bước 3:** *"Viết Frontend kết nối vào API vừa viết."*

### Mẹo 4: "Ping-pong" (Tranh luận) với Giáo sư AI
Hệ thống đã được lập trình để đóng vai một Giáo sư phản biện cực kỳ khắt khe. Hãy tận dụng điều này để rèn luyện kỹ năng bảo vệ đồ án:
* **Cách kích hoạt:** *"Hãy đọc file `Thuyết minh.md` và đóng vai hội đồng phản biện. Đặt cho tôi 3 câu hỏi hóc búa nhất về tính khả thi của đề tài này."*
* **Lợi ích:** Trám kín mọi lỗ hổng logic trước khi nộp bài thật.

### Mẹo 5: Yêu cầu AI Lướt Web & Mở Trình Duyệt
AI có quyền truy cập Internet và có thể tự động bật một trình duyệt ảo để làm thay bạn.
* **Cách kích hoạt (Tìm kiếm):** *"Lên mạng tìm hiểu cho tôi thuật toán Collaborative Filtering trong bài toán ghép cặp sinh viên."*
* **Cách kích hoạt (Mở web/Test UI):** *"Sử dụng kỹ năng `browser_subagent` để mở trang `http://localhost:3000`, thử nhập form đăng nhập và chụp màn hình lại cho tôi xem giao diện hiện tại."*

### Mẹo 6: Kết nối Dịch vụ ngoài bằng MCP Server
Hệ thống được cấu hình ưu tiên bảo mật thông qua giao thức MCP. Bạn có thể sai AI làm các "gig" trên Internet.
* **Chuẩn bị:** Đảm bảo bạn đã khởi động MCP Server (Ví dụ: Github MCP, Google Drive MCP).
* **Cách kích hoạt:** *"Hãy dùng Github MCP để tạo một Repository mới, sau đó commit toàn bộ file mã nguồn hiện tại lên nhánh main."*
* **Lưu ý bảo mật:** AI sẽ không bao giờ hỏi mật khẩu của bạn. Mọi thao tác xác thực diễn ra ngầm trong MCP. Nếu AI cần quyền, nó sẽ hiển thị cửa sổ `Allow Permission`, bạn chỉ việc bấm Chấp nhận.

### Mẹo 7: "Sang tên đổi chủ" (Meta-Configuration)
Nếu dự án đổi định hướng, bạn không cần phải tự sửa từng file cấu hình của AI. Tính năng Meta-Config cho phép AI **tự sửa chính mã gen của nó**.
* **Cách kích hoạt:** Gõ lệnh `/config [Định hướng mới]`
* **Ví dụ:** `/config Dự án NCKH này đã xong. Từ giờ hãy chuyển template thành dự án làm Web bán nhà trọ SaaS. Đổi giọng văn sang phong cách Sale.`
* AI sẽ tự động rà soát file `GEMINI.md`, gỡ luật học thuật, thêm luật kinh doanh và báo cáo lại cho bạn.

---

## 4. Xử lý Sự Cố Kỹ Thuật (Troubleshooting)

* **Lỗi `Access is denied` ở Terminal:** Do hệ thống bảo mật Sandbox của Windows chặn AI tự chạy lệnh. Cách xử lý: **Hãy làm đôi tay cho AI**. Copy câu lệnh AI gợi ý, tự dán vào Terminal/PowerShell của bạn, chạy xong thì copy cái Logs kết quả dán lại vào khung chat cho AI phân tích.
* **Lỗi "Quên ngữ cảnh":** Nếu chat quá dài, AI có thể bị trôi ý. Hãy chủ động nhắc lại: *"Hãy đọc lại file `Technical_Specification.md` trước khi làm bước tiếp theo"*.

---
> **Tham khảo thêm:**
> Danh sách toàn bộ 573 kỹ năng (Có tiếng Việt) nằm tại: `NCKH/.agent/SKILLS_INVENTORY_VI.md`.
