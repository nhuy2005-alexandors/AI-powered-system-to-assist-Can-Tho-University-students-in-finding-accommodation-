# 📑 ĐẶC TẢ USE CASE — HỆ THỐNG TỔNG HỢP & GỢI Ý NHÀ TRỌ AI
**Đề tài:** THS2026-66  
**Phiên bản:** 1.0  
**Ngày cập nhật:** 10/06/2026

---

## MỤC LỤC

1. [Giới thiệu](#1-giới-thiệu)
2. [Danh sách Actors](#2-danh-sách-actors)
3. [Sơ đồ Use Case tổng quan](#3-sơ-đồ-use-case-tổng-quan)
4. [Đặc tả Use Case chi tiết — Nhóm A (Nền tảng Web)](#4-đặc-tả-use-case-chi-tiết--nhóm-a)
5. [Đặc tả Use Case chi tiết — Nhóm B (AI)](#5-đặc-tả-use-case-chi-tiết--nhóm-b)
6. [Đặc tả Use Case chi tiết — Nhóm C (Hệ thống & Admin)](#6-đặc-tả-use-case-chi-tiết--nhóm-c)
7. [Activity Diagrams](#7-activity-diagrams)

---

## 1. GIỚI THIỆU

### 1.1 Mục đích tài liệu
Tài liệu này mô tả đầy đủ các Use Case của hệ thống "Tổng hợp và Gợi ý Nhà trọ ứng dụng AI hỗ trợ sinh viên ĐH Cần Thơ". Mỗi Use Case được đặc tả theo chuẩn Cockburn với: Actor, Điều kiện tiên quyết, Luồng chính, Luồng thay thế, và Điều kiện sau.

### 1.2 Phạm vi hệ thống
- Hệ thống hoạt động theo mô hình **Aggregator (Bộ tổng hợp thông minh)**.
- Dữ liệu nhà trọ được crawl tự động từ các nền tảng trực tuyến (Phongtro123, Chotot, Mogi) và bổ sung bởi cộng đồng sinh viên.
- Cung cấp dữ liệu ở mức **gần thời gian thực (near real-time)** với chu kỳ cập nhật 6–12 giờ.
- **Ngoài phạm vi:** Xác nhận phòng còn trống hay đã cho thuê — người dùng tự xác nhận qua link nguồn gốc.

---

## 2. DANH SÁCH ACTORS

| Actor | Mô tả | Quyền |
|---|---|---|
| **Guest (Khách)** | Người truy cập chưa đăng nhập. Có thể xem, tìm kiếm, lọc tin nhà trọ. | Chỉ đọc |
| **User (Người dùng / Sinh viên)** | Đã đăng nhập. Kế thừa toàn bộ quyền Guest, thêm: dùng AI gợi ý, chatbot, matching, lưu yêu thích, đăng tin, báo cáo. | Đọc + Ghi |
| **Admin (Quản trị viên)** | Quản lý nội dung, kiểm duyệt, cấu hình hệ thống. | Toàn quyền |
| **System (Hệ thống tự động)** | Crawler, AI Pipeline, Scheduled Jobs. Không có giao diện người dùng. | Xử lý nền |

---

## 3. SƠ ĐỒ USE CASE TỔNG QUAN

> File PlantUML (có thể chỉnh sửa): `Diagrams/UseCase_Diagram.puml`
> File ảnh đã render: `Diagrams/UseCase_TroThongMinh.png`

---

## 4. ĐẶC TẢ USE CASE CHI TIẾT — NHÓM A (NỀN TẢNG WEB)

---

### UC-A1.1: Đăng ký tài khoản

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A1.1 |
| **Tên** | Đăng ký tài khoản |
| **Actor chính** | Guest |
| **Mô tả** | Người dùng tạo tài khoản mới bằng Email + Mật khẩu, xác thực qua OTP email. |
| **Điều kiện tiên quyết** | Chưa có tài khoản với email đó trong hệ thống. |
| **Luồng chính** | 1. Guest bấm "Đăng ký".<br>2. Hệ thống hiển thị form: Email, Mật khẩu, Xác nhận MK, Tên hiển thị.<br>3. Guest điền thông tin, bấm "Đăng ký".<br>4. Hệ thống validate (email hợp lệ, MK >= 8 ký tự, 2 MK trùng nhau).<br>5. Hệ thống gửi mã OTP 6 số qua email.<br>6. Guest nhập OTP.<br>7. Hệ thống xác thực OTP, tạo tài khoản, chuyển hướng đến Onboarding Quiz (UC-B1.1). |
| **Luồng thay thế** | 4a. Email đã tồn tại → Thông báo "Email đã được sử dụng".<br>4b. MK không đủ mạnh → Hiển thị lỗi validate.<br>6a. OTP sai → Cho phép nhập lại (tối đa 3 lần).<br>6b. OTP hết hạn (5 phút) → Bấm "Gửi lại OTP". |
| **Điều kiện sau** | Tài khoản được tạo với role = "user", chuyển đến Onboarding Quiz. |

---

### UC-A1.2: Đăng nhập

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A1.2 |
| **Tên** | Đăng nhập |
| **Actor chính** | Guest |
| **Mô tả** | Đăng nhập bằng Email + Mật khẩu, nhận JWT Token. |
| **Điều kiện tiên quyết** | Đã có tài khoản. |
| **Luồng chính** | 1. Guest bấm "Đăng nhập".<br>2. Nhập Email + Mật khẩu.<br>3. Hệ thống xác thực, tạo JWT Access Token (15 phút) + Refresh Token (7 ngày).<br>4. Chuyển hướng về trang chủ với vai trò User. |
| **Luồng thay thế** | 3a. Sai mật khẩu → Thông báo "Email hoặc mật khẩu không đúng" (không chỉ rõ cái nào sai).<br>3b. Sai quá 5 lần → Khóa tạm 15 phút. |
| **Điều kiện sau** | JWT Token được lưu (httpOnly cookie), User có phiên đăng nhập. |

---

### UC-A1.3: Đăng nhập Google (OAuth 2.0)

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A1.3 |
| **Tên** | Đăng nhập bằng Google |
| **Actor chính** | Guest |
| **Mô tả** | One-click đăng nhập bằng tài khoản Google. Nếu chưa có tài khoản, tự tạo mới. |
| **Luồng chính** | 1. Guest bấm "Đăng nhập bằng Google".<br>2. Redirect sang Google OAuth Consent Screen.<br>3. User cấp quyền (email, tên, avatar).<br>4. Google trả Authorization Code.<br>5. Backend đổi Code lấy ID Token, trích xuất email, tên, avatar.<br>6a. Nếu email chưa tồn tại → Tạo tài khoản mới (provider = 'google').<br>6b. Nếu email đã tồn tại → Đăng nhập vào tài khoản đó.<br>7. Cấp JWT Token. |
| **Điều kiện sau** | User đăng nhập thành công. Nếu tài khoản mới → Chuyển đến Onboarding Quiz. |

---

### UC-A1.4: Quên mật khẩu

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A1.4 |
| **Tên** | Quên mật khẩu |
| **Actor chính** | Guest |
| **Luồng chính** | 1. Bấm "Quên mật khẩu".<br>2. Nhập email.<br>3. Hệ thống gửi link đặt lại MK (hết hạn 30 phút).<br>4. User mở link, nhập MK mới.<br>5. Hệ thống cập nhật password_hash. |
| **Luồng thay thế** | 2a. Email không tồn tại → Vẫn hiển thị "Đã gửi email" (tránh leak thông tin).<br>4a. Link hết hạn → Yêu cầu gửi lại. |

---

### UC-A2.1: Tìm kiếm nhà trọ

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A2.1 |
| **Tên** | Tìm kiếm nhà trọ |
| **Actor chính** | Guest / User |
| **Mô tả** | Tìm kiếm nhà trọ bằng từ khóa, lọc đa tiêu chí, sắp xếp, xem trên bản đồ. |
| **Điều kiện tiên quyết** | Không (có thể dùng mà không cần đăng nhập). |
| **Luồng chính** | 1. Nhập từ khóa vào thanh tìm kiếm (tên đường, khu vực).<br>2. Hệ thống hiển thị kết quả kèm sidebar bộ lọc.<br>3. Áp dụng bộ lọc: Khoảng giá (slider), Diện tích (min-max), Quận/Phường (dropdown), Tiện ích (checkbox: wifi, máy lạnh, WC riêng, gác lửng...), Khoảng cách đến CTU (slider).<br>4. Chọn sắp xếp: Giá tăng / Giá giảm / Mới nhất / Gần CTU nhất / Điểm an sinh cao nhất.<br>5. Hệ thống trả về danh sách kết quả (paginated, 20 tin/trang).<br>6. Chuyển đổi giữa List View và Map View. |
| **Luồng thay thế** | 1a. Không nhập từ khóa → Hiển thị tất cả, lọc bằng sidebar.<br>6a. Map View: Hiển thị pin trên bản đồ Leaflet/OSM, click pin → popup tóm tắt. |
| **Điều kiện sau** | Danh sách kết quả hiển thị, mỗi item kèm badge rủi ro và thời gian cập nhật. |
| **Include** | UC-A2.2 (Lọc), UC-A2.3 (Sắp xếp) |

---

### UC-A2.5: Tìm theo bán kính trên bản đồ

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A2.5 |
| **Tên** | Tìm theo bán kính |
| **Actor chính** | Guest / User |
| **Luồng chính** | 1. Trong Map View, click vào 1 điểm trên bản đồ (hoặc chọn "Vị trí CTU").<br>2. Kéo slider chọn bán kính (500m - 5km).<br>3. Hệ thống vẽ vòng tròn, query PostGIS: `ST_DWithin(geom, center, radius)`.<br>4. Chỉ hiện phòng trọ nằm trong vòng tròn. |

---

### UC-A3.1: Xem chi tiết nhà trọ

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A3.1 |
| **Tên** | Xem chi tiết nhà trọ |
| **Actor chính** | Guest / User |
| **Luồng chính** | 1. Click vào 1 tin nhà trọ từ danh sách hoặc bản đồ.<br>2. Hệ thống hiển thị trang chi tiết: Gallery ảnh (carousel), Giá, Diện tích, Địa chỉ, Danh sách tiện ích, Bản đồ mini + POI lân cận (đồn CA, BV, trạm bus), Badge rủi ro (xanh/vàng/đỏ), Nguồn gốc + link gốc, "Cập nhật lần cuối: X ngày trước".<br>3. Disclaimer: "Hệ thống tổng hợp thông tin. Vui lòng liên hệ trực tiếp để xác nhận." |
| **Extend** | UC-A3.2 (Lưu yêu thích), UC-A3.5 (Báo cáo), UC-A3.4 (Chia sẻ) |

---

### UC-A3.2: Lưu tin yêu thích

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A3.2 |
| **Tên** | Lưu tin yêu thích |
| **Actor chính** | User |
| **Điều kiện tiên quyết** | Đã đăng nhập. |
| **Luồng chính** | 1. Bấm icon ♡ trên tin nhà trọ.<br>2. Tin được thêm vào danh sách "Yêu thích" (bảng favorites).<br>3. Icon đổi thành ♥ (đã lưu).<br>4. Bấm lại → Bỏ yêu thích. |
| **Luồng thay thế** | 1a. Chưa đăng nhập → Hiện popup "Đăng nhập để lưu tin". |

---

### UC-A3.3: So sánh phòng trọ

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A3.3 |
| **Tên** | So sánh phòng trọ |
| **Actor chính** | User |
| **Luồng chính** | 1. Bấm "Thêm vào so sánh" trên 2-3 tin (tối đa 3).<br>2. Bấm "So sánh ngay".<br>3. Hệ thống hiển thị bảng so sánh side-by-side: Giá, Diện tích, Tiện ích, Khoảng cách CTU, Khoảng cách đồn CA, Risk Score. |

---

### UC-A3.5: Báo cáo tin sai

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A3.5 |
| **Tên** | Báo cáo tin sai |
| **Actor chính** | User |
| **Luồng chính** | 1. Bấm nút "Báo cáo" trên trang chi tiết.<br>2. Chọn lý do: Sai giá / Tin cũ / Lừa đảo / Khác.<br>3. Nhập ghi chú (tùy chọn).<br>4. Hệ thống lưu vào bảng reports, status = 'pending'.<br>5. Admin nhận thông báo. |

---

### UC-A4.1: Đăng tin nhà trọ mới (UGC)

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A4.1 |
| **Tên** | Đăng tin nhà trọ mới |
| **Actor chính** | User |
| **Điều kiện tiên quyết** | Đã đăng nhập. |
| **Luồng chính** | 1. Bấm "Đăng tin".<br>2. Điền form: Tiêu đề, Giá, Diện tích, Địa chỉ, Upload ảnh (tối đa 10), Mô tả, Chọn tiện ích (checkbox).<br>3. Bấm "Đăng".<br>4. Hệ thống chạy AI Risk Check tự động.<br>5a. Risk score < ngưỡng → Tin được đăng ngay, source = 'ugc'.<br>5b. Risk score >= ngưỡng → Tin chờ Admin kiểm duyệt. |
| **Luồng thay thế** | 2a. Thiếu trường bắt buộc → Hiển thị lỗi validate.<br>2b. Ảnh quá lớn (> 5MB) → Yêu cầu nén lại. |
| **Include** | UC-B4 (AI Risk Check) |

---

### UC-A5.1: Nhận thông báo tin mới phù hợp

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-A5.1 |
| **Tên** | Thông báo tin mới phù hợp |
| **Actor chính** | User |
| **Luồng chính** | 1. Khi crawler tìm thấy tin mới.<br>2. Hệ thống so khớp tin mới với preference vector của tất cả User.<br>3. Nếu Cosine Similarity > ngưỡng → Gửi push notification / email cho User.<br>4. Nội dung: "Có phòng mới phù hợp: [Tiêu đề], [Giá], [Khu vực]". |

---

## 5. ĐẶC TẢ USE CASE CHI TIẾT — NHÓM B (AI)

---

### UC-B1.1: Onboarding Quiz

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-B1.1 |
| **Tên** | Điền Onboarding Quiz |
| **Actor chính** | User |
| **Mô tả** | 3 câu hỏi nhanh khi đăng ký lần đầu để tạo preference vector khởi tạo cho AI. |
| **Điều kiện tiên quyết** | Vừa đăng ký xong hoặc chưa điền quiz. |
| **Luồng chính** | 1. Hệ thống hiển thị 3 câu hỏi:<br>   Q1: "Ngân sách hàng tháng?" → Slider (500K - 5M VNĐ).<br>   Q2: "Khoảng cách tối đa đến CTU?" → Slider (500m - 5km).<br>   Q3: "Tiện ích bắt buộc?" → Checkbox (Wifi, Máy lạnh, WC riêng, Gác lửng, Chỗ để xe).<br>2. Bấm "Hoàn tất".<br>3. Hệ thống chuyển câu trả lời thành preference_vector, lưu vào bảng users. |
| **Luồng thay thế** | 1a. Bấm "Bỏ qua" → Dùng Popularity-Based gợi ý thay vì AI. |
| **Điều kiện sau** | User có preference_vector, module AI Recommendation bắt đầu hoạt động. |

---

### UC-B1.2: Xem gợi ý "Dành cho bạn"

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-B1.2 |
| **Tên** | Gợi ý cá nhân hóa |
| **Actor chính** | User |
| **Mô tả** | Trang chủ hiển thị Top-10 phòng phù hợp nhất dựa trên preference vector + implicit feedback. |
| **Luồng chính** | 1. User mở trang chủ.<br>2. Hệ thống lấy preference_vector của User.<br>3. Tính Cosine Similarity giữa user vector và TẤT CẢ listing vector (chỉ tin status = 'active').<br>4. Sắp xếp giảm dần, lấy Top-10.<br>5. Hiển thị section "Dành cho bạn" trên trang chủ. |
| **Luồng thay thế** | 2a. User chưa có preference_vector → Hiển thị "Top phổ biến tuần này" (Popularity-Based). |
| **Extend** | UC-B1.4 (Tab Khám phá: 80% AI + 20% random) |

---

### UC-B2.1: Tìm bạn ở ghép

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-B2.1 |
| **Tên** | Tìm bạn ở ghép |
| **Actor chính** | User |
| **Mô tả** | Tìm bạn ở ghép hòa hợp dựa trên khảo sát tính cách (Forced Choice). |
| **Điều kiện tiên quyết** | Đã đăng nhập + Đã điền hồ sơ ở ghép. |
| **Luồng chính** | 1. Bấm "Tìm bạn ở ghép".<br>2. Nếu chưa có hồ sơ → Chuyển đến UC-B2.1a (Điền hồ sơ).<br>3. Hệ thống tính Weighted Cosine Similarity với tất cả roommate_profiles.<br>4. Lọc: Score >= 0.7.<br>5. Hiển thị danh sách: Avatar, Tên, Score (%), Tóm tắt thói quen.<br>6. Click xem chi tiết → Xem hồ sơ đầy đủ.<br>7. Bấm "Gửi lời mời kết nối" → Nhập lời giới thiệu → Gửi. |
| **Luồng thay thế** | 4a. Không có ai Score >= 0.7 → "Chưa tìm thấy bạn ghép phù hợp. Hệ thống sẽ thông báo khi có người mới đăng ký." |

**UC-B2.1a: Điền hồ sơ ở ghép (Forced Choice)**

| Câu hỏi tình huống | Lựa chọn | Trọng số |
|---|---|---|
| "Ngân sách ở ghép hàng tháng?" | Slider 500K - 3M | 25% |
| "Bạn thường ngủ lúc mấy giờ?" | Trước 10h / 10-12h / Sau 12h | 20% |
| "Bạn cùng phòng bật nhạc lúc 11h đêm, bạn sẽ?" | Nhờ tắt / OK nếu nhỏ / Không quan tâm | 15% |
| "Mức độ dọn dẹp phòng?" | Mỗi ngày / Vài ngày / Khi nào rảnh | 15% |
| "Bạn có hút thuốc?" | Có / Không | 15% |
| "Giới tính bạn ghép mong muốn?" | Nam / Nữ / Không quan tâm | 10% |

---

### UC-B3.1: Chatbot hỏi đáp AI (RAG)

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-B3.1 |
| **Tên** | Chatbot hỏi đáp AI |
| **Actor chính** | User |
| **Mô tả** | Hỏi bằng ngôn ngữ tự nhiên, chatbot trả lời dựa trên dữ liệu phòng trọ thực trong DB (RAG Pipeline). |
| **Điều kiện tiên quyết** | Đã đăng nhập. Vector DB đã được index. |
| **Luồng chính** | 1. Bấm icon chatbot (góc phải dưới màn hình).<br>2. Nhập câu hỏi: VD "Phòng 1.5 triệu gần CTU có wifi?".<br>3. Hệ thống nhúng câu hỏi thành vector (multilingual-e5-small).<br>4. Similarity Search trong pgvector → Top-5 phòng liên quan nhất + score.<br>5a. Best score >= 0.65 → Tạo Prompt (context = 5 phòng + chỉ số POI) → Gửi cho Gemini 1.5 Flash → Trả lời bằng ngôn ngữ tự nhiên + link đến phòng cụ thể.<br>5b. Best score < 0.65 → Trả lời: "Tôi không tìm thấy thông tin phù hợp. Bạn thử tiêu chí khác nhé!" + Link trang tìm kiếm.<br>6. Lưu hội thoại vào Conversation Memory (5 lượt). |
| **Luồng thay thế** | 2a. Câu hỏi không liên quan đến nhà trọ → LLM trả lời: "Tôi chỉ hỗ trợ tìm nhà trọ. Bạn muốn tìm phòng ở khu vực nào?" |
| **Điều kiện sau** | Câu trả lời hiển thị + Memory được cập nhật cho multi-turn. |

---

### UC-B4.1: Xem badge rủi ro

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-B4.1 |
| **Tên** | Xem badge cảnh báo rủi ro |
| **Actor chính** | Guest / User |
| **Mô tả** | Mỗi tin nhà trọ hiển thị badge rủi ro được AI tính tự động. |
| **Luồng chính** | 1. Trên mỗi tin, hiển thị badge:<br>   - ✅ "An toàn" (risk_score < 0.3)<br>   - ⚠️ "Cần kiểm chứng" (0.3 ≤ risk_score < 0.6)<br>   - 🔴 "Nghi vấn" (risk_score ≥ 0.6)<br>2. Click badge → Popup hiển thị lý do cụ thể từ risk_reasons[]:<br>   - "Giá thấp hơn 40% so với khu vực"<br>   - "Không có ảnh thực tế"<br>   - "Mô tả chứa từ khóa đáng ngờ" |

---

## 6. ĐẶC TẢ USE CASE CHI TIẾT — NHÓM C (HỆ THỐNG & ADMIN)

---

### UC-C1.1: Crawl dữ liệu tự động

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-C1.1 |
| **Tên** | Crawl dữ liệu tự động |
| **Actor chính** | System |
| **Mô tả** | Crawler chạy định kỳ 6-12h, lấy dữ liệu nhà trọ từ các trang web nguồn. |
| **Luồng chính** | 1. Cron job trigger (mỗi 6h).<br>2. Đọc danh sách nguồn + CSS selectors từ config JSON.<br>3. Với mỗi nguồn: Gửi HTTP requests (rate limit 1 req/5s, xoay User-Agent).<br>4. Parse HTML → Trích xuất: Tiêu đề, Giá, DT, Địa chỉ, Ảnh, Mô tả.<br>5. NLP trích xuất tiện ích từ mô tả (UC-C1.2).<br>6. Geocoding đa tầng (UC-C1.4).<br>7. MinHash + LSH lọc trùng lặp (UC-C1.3).<br>8. PostGIS tính khoảng cách POI (UC-C1.5).<br>9. AI Risk Check (UC-B4).<br>10. Nhúng vector cho RAG (UC-C1.6).<br>11. INSERT/UPDATE vào aggregated_listings. |
| **Luồng thay thế** | 3a. Bị block (403/429) → Log lỗi, gửi alert cho Admin, bỏ qua nguồn đó.<br>4a. HTML thay đổi layout → Parser trả null → Log lỗi. |
| **Điều kiện sau** | DB được cập nhật tin mới. Health check chạy: nếu < 10 tin mới → Cảnh báo. |

---

### UC-C2.1: Admin Dashboard

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-C2.1 |
| **Tên** | Xem Dashboard tổng quan |
| **Actor chính** | Admin |
| **Luồng chính** | 1. Admin đăng nhập, truy cập /admin.<br>2. Hiển thị: Tổng số tin (active/stale), Tin mới hôm nay, Tin bị report, Crawler status (lần chạy cuối, số tin mỗi nguồn), Số user đăng ký, Top phòng được xem nhiều nhất. |

---

### UC-C2.2: Kiểm duyệt tin bị flagged

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-C2.2 |
| **Tên** | Kiểm duyệt tin |
| **Actor chính** | Admin |
| **Luồng chính** | 1. Xem danh sách tin: risk_score cao + tin bị report.<br>2. Mỗi tin hiển thị: Nội dung tin, Lý do flagged, Số lượt report, Risk reasons.<br>3. Admin chọn: "Duyệt" (giữ nguyên) / "Ẩn" (không hiển thị) / "Xóa" (xóa vĩnh viễn). |

---

## 7. ACTIVITY DIAGRAMS

Các Activity Diagram mô tả luồng xử lý chính của hệ thống. File `.puml` có thể chỉnh sửa trực tiếp, file `.png` là ảnh đã render.

| # | Tên Diagram | File PlantUML | File Ảnh |
|---|---|---|---|
| 1 | Luồng Tìm kiếm & Gợi ý | `Activity_TimKiem_GoiY.puml` | `Activity_TimKiem_GoiY.png` |
| 2 | Luồng Chatbot RAG | `Activity_Chatbot_RAG.puml` | `Activity_Chatbot_RAG.png` |
| 3 | Luồng Crawler Pipeline | `Activity_Crawler_Pipeline.puml` | `Activity_Crawler_Pipeline.png` |
| 4 | Luồng Matching Bạn Ghép | `Activity_Matching_BanGhep.puml` | `Activity_Matching_BanGhep.png` |

### Cách chỉnh sửa diagram:
1. Mở file `.puml` bằng VS Code (cài extension "PlantUML").
2. Chỉnh sửa nội dung text.
3. Render lại bằng lệnh:
```bash
java -jar Diagrams/tools/plantuml.jar -tpng -charset UTF-8 <file.puml>
```
