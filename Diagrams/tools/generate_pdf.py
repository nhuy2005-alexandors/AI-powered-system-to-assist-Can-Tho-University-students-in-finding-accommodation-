"""
Script tạo PDF Đặc tả Use Case từ dữ liệu hệ thống.
Sử dụng HTML + CSS và weasyprint để render PDF chất lượng cao.
"""
import sys

try:
    from weasyprint import HTML
    USE_WEASYPRINT = True
except (ImportError, OSError):
    USE_WEASYPRINT = False
    print("weasyprint không khả dụng, sẽ tạo file HTML thay thế.")

HTML_CONTENT = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Đặc Tả Use Case — Hệ Thống Tổng Hợp & Gợi Ý Nhà Trọ AI</title>
<style>
  @page {
    size: A4 landscape;
    margin: 1.5cm;
  }
  body {
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 9pt;
    color: #1a1a1a;
    line-height: 1.5;
  }
  h1 {
    text-align: center;
    color: #1565C0;
    font-size: 16pt;
    margin-bottom: 5px;
    border-bottom: 3px solid #1565C0;
    padding-bottom: 10px;
  }
  h2 {
    color: #2E7D32;
    font-size: 12pt;
    margin-top: 25px;
    margin-bottom: 10px;
    padding: 5px 10px;
    background: #E8F5E9;
    border-left: 4px solid #2E7D32;
  }
  h3 {
    color: #E65100;
    font-size: 10pt;
    margin-top: 15px;
  }
  .subtitle {
    text-align: center;
    color: #666;
    font-size: 9pt;
    margin-bottom: 20px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 15px;
    page-break-inside: avoid;
  }
  th {
    background-color: #1565C0;
    color: white;
    padding: 6px 8px;
    text-align: left;
    font-size: 8.5pt;
    font-weight: 600;
  }
  td {
    padding: 5px 8px;
    border: 1px solid #ddd;
    vertical-align: top;
    font-size: 8.5pt;
  }
  tr:nth-child(even) { background-color: #f8f9fa; }
  tr:hover { background-color: #e3f2fd; }
  .id { font-weight: bold; color: #1565C0; white-space: nowrap; }
  .actor { white-space: nowrap; }
  .flow { font-size: 8pt; }
  .tag-ai { background: #E8F5E9; color: #2E7D32; padding: 1px 5px; border-radius: 3px; font-size: 7.5pt; font-weight: bold; }
  .tag-sys { background: #E3F2FD; color: #1565C0; padding: 1px 5px; border-radius: 3px; font-size: 7.5pt; font-weight: bold; }
  .tag-web { background: #FFF3E0; color: #E65100; padding: 1px 5px; border-radius: 3px; font-size: 7.5pt; font-weight: bold; }
  .note { background: #FFFDE7; border-left: 3px solid #F9A825; padding: 8px; margin: 10px 0; font-size: 8.5pt; }
  .footer { text-align: center; color: #999; font-size: 7pt; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 5px; }
</style>
</head>
<body>

<h1>📑 ĐẶC TẢ USE CASE</h1>
<div class="subtitle">
  Hệ Thống Tổng Hợp & Gợi Ý Nhà Trọ Ứng Dụng AI — THS2026-66<br>
  Phiên bản 1.0 · Ngày: 10/06/2026
</div>

<div class="note">
  <strong>Phạm vi:</strong> Hệ thống hoạt động theo mô hình Aggregator (tổng hợp thông minh). 
  Dữ liệu ở mức gần thời gian thực (6–12h). Việc xác nhận phòng còn trống nằm ngoài phạm vi.
</div>

<!-- ═══════════════════════════════════ -->
<h2>NHÓM A — NỀN TẢNG WEB CƠ BẢN</h2>

<table>
<tr>
  <th style="width:7%">ID</th>
  <th style="width:10%">Tên UC</th>
  <th style="width:6%">Actor</th>
  <th style="width:12%">Mô tả</th>
  <th style="width:10%">Điều kiện tiên quyết</th>
  <th style="width:25%">Luồng chính</th>
  <th style="width:20%">Luồng thay thế / Ngoại lệ</th>
  <th style="width:10%">Điều kiện sau</th>
</tr>

<tr>
  <td class="id">UC-A1.1</td>
  <td>Đăng ký tài khoản</td>
  <td class="actor">Guest</td>
  <td>Tạo tài khoản mới bằng Email + MK, xác thực OTP email.</td>
  <td>Email chưa tồn tại trong hệ thống.</td>
  <td class="flow">1. Guest bấm "Đăng ký".<br>2. Hiển thị form: Email, MK, Xác nhận MK, Tên.<br>3. Điền thông tin, bấm "Đăng ký".<br>4. Validate (email hợp lệ, MK ≥ 8 ký tự).<br>5. Gửi mã OTP 6 số qua email.<br>6. Nhập OTP.<br>7. Xác thực, tạo TK → Onboarding Quiz.</td>
  <td class="flow">4a. Email đã tồn tại → Báo lỗi.<br>4b. MK yếu → Hiển thị lỗi validate.<br>6a. OTP sai → Nhập lại (tối đa 3 lần).<br>6b. OTP hết hạn (5p) → Gửi lại.</td>
  <td>TK được tạo (role=user), chuyển đến Onboarding Quiz.</td>
</tr>

<tr>
  <td class="id">UC-A1.2</td>
  <td>Đăng nhập</td>
  <td class="actor">Guest</td>
  <td>Đăng nhập Email/Password, nhận JWT Token.</td>
  <td>Đã có tài khoản.</td>
  <td class="flow">1. Bấm "Đăng nhập".<br>2. Nhập Email + MK.<br>3. Xác thực → JWT Access Token (15p) + Refresh Token (7 ngày).<br>4. Chuyển về trang chủ.</td>
  <td class="flow">3a. Sai MK → "Email hoặc MK không đúng".<br>3b. Sai > 5 lần → Khóa tạm 15 phút.</td>
  <td>JWT lưu httpOnly cookie, User có phiên đăng nhập.</td>
</tr>

<tr>
  <td class="id">UC-A1.3</td>
  <td>Đăng nhập Google (OAuth 2.0)</td>
  <td class="actor">Guest</td>
  <td>One-click đăng nhập bằng Google. Tự tạo TK nếu chưa có.</td>
  <td>Không.</td>
  <td class="flow">1. Bấm "Đăng nhập bằng Google".<br>2. Redirect → Google Consent Screen.<br>3. Cấp quyền (email, tên, avatar).<br>4. Google trả Authorization Code.<br>5. Backend đổi Code → ID Token.<br>6a. Email chưa có → Tạo TK mới (provider='google').<br>6b. Email đã có → Đăng nhập TK cũ.<br>7. Cấp JWT.</td>
  <td class="flow">3a. User từ chối cấp quyền → Quay lại trang login.</td>
  <td>Đăng nhập thành công. TK mới → Onboarding Quiz.</td>
</tr>

<tr>
  <td class="id">UC-A1.4</td>
  <td>Quên mật khẩu</td>
  <td class="actor">Guest</td>
  <td>Gửi link đặt lại MK qua email.</td>
  <td>Đã có TK.</td>
  <td class="flow">1. Bấm "Quên MK".<br>2. Nhập email.<br>3. Gửi link reset (hết hạn 30p).<br>4. Mở link, nhập MK mới.<br>5. Cập nhật password_hash.</td>
  <td class="flow">2a. Email không tồn tại → Vẫn hiện "Đã gửi" (tránh leak).<br>4a. Link hết hạn → Gửi lại.</td>
  <td>MK được đổi thành công.</td>
</tr>

<tr>
  <td class="id">UC-A1.5</td>
  <td>Quản lý hồ sơ cá nhân</td>
  <td class="actor">User</td>
  <td>Đổi avatar, tên, SĐT, mật khẩu.</td>
  <td>Đã đăng nhập.</td>
  <td class="flow">1. Vào "Hồ sơ cá nhân".<br>2. Chỉnh sửa thông tin.<br>3. Bấm "Lưu".<br>4. Validate + cập nhật DB.</td>
  <td class="flow">4a. SĐT sai định dạng → Báo lỗi.</td>
  <td>Thông tin được cập nhật.</td>
</tr>

<tr>
  <td class="id">UC-A2.1</td>
  <td>Tìm kiếm nhà trọ</td>
  <td class="actor">Guest / User</td>
  <td>Tìm bằng từ khóa + lọc đa tiêu chí + sắp xếp + bản đồ.</td>
  <td>Không (không cần đăng nhập).</td>
  <td class="flow">1. Nhập từ khóa (tên đường, khu vực).<br>2. Hiển thị kết quả + sidebar lọc.<br>3. Lọc: Giá (slider), DT, Quận, Tiện ích (checkbox), Khoảng cách CTU.<br>4. Sắp xếp: Giá ↑↓ / Mới nhất / Gần nhất.<br>5. Trả về kết quả (20 tin/trang).<br>6. Chuyển đổi List View / Map View.</td>
  <td class="flow">1a. Không nhập từ khóa → Hiện tất cả, lọc bằng sidebar.<br>6a. Map View: Pin trên Leaflet/OSM, click → popup.</td>
  <td>Danh sách kết quả + badge rủi ro + timestamp.</td>
</tr>

<tr>
  <td class="id">UC-A2.5</td>
  <td>Tìm theo bán kính</td>
  <td class="actor">Guest / User</td>
  <td>Vẽ vòng tròn trên bản đồ, chỉ hiện phòng trong bán kính.</td>
  <td>Đang ở Map View.</td>
  <td class="flow">1. Click 1 điểm trên bản đồ (hoặc chọn "CTU").<br>2. Kéo slider bán kính (500m – 5km).<br>3. PostGIS: ST_DWithin(geom, center, radius).<br>4. Chỉ hiển thị phòng trong vòng tròn.</td>
  <td class="flow">—</td>
  <td>Kết quả được lọc theo không gian.</td>
</tr>

<tr>
  <td class="id">UC-A3.1</td>
  <td>Xem chi tiết nhà trọ</td>
  <td class="actor">Guest / User</td>
  <td>Trang chi tiết đầy đủ: ảnh, giá, bản đồ, risk badge, nguồn gốc.</td>
  <td>Không.</td>
  <td class="flow">1. Click 1 tin từ danh sách/bản đồ.<br>2. Hiển thị: Gallery ảnh, Giá, DT, Địa chỉ, Tiện ích, Bản đồ mini + POI (đồn CA, BV, bus), Badge rủi ro, Nguồn gốc + link, "Cập nhật: X ngày trước".<br>3. Disclaimer: "Vui lòng liên hệ trực tiếp để xác nhận."</td>
  <td class="flow">—</td>
  <td>Thông tin chi tiết hiển thị. Extend: Lưu ♡, Báo cáo, Chia sẻ.</td>
</tr>

<tr>
  <td class="id">UC-A3.2</td>
  <td>Lưu tin yêu thích</td>
  <td class="actor">User</td>
  <td>Bookmark phòng trọ → Xem lại trong "Yêu thích".</td>
  <td>Đã đăng nhập.</td>
  <td class="flow">1. Bấm ♡ trên tin.<br>2. Lưu vào bảng favorites.<br>3. Icon đổi ♥.<br>4. Bấm lại → Bỏ yêu thích.</td>
  <td class="flow">1a. Chưa đăng nhập → Popup "Đăng nhập để lưu".</td>
  <td>Tin được thêm/xóa khỏi danh sách yêu thích.</td>
</tr>

<tr>
  <td class="id">UC-A3.3</td>
  <td>So sánh phòng trọ</td>
  <td class="actor">User</td>
  <td>So sánh side-by-side 2–3 phòng.</td>
  <td>Đã đăng nhập.</td>
  <td class="flow">1. Bấm "Thêm vào so sánh" trên 2–3 tin (tối đa 3).<br>2. Bấm "So sánh ngay".<br>3. Bảng so sánh: Giá, DT, Tiện ích, Khoảng cách CTU, Khoảng cách CA, Risk.</td>
  <td class="flow">1a. Thêm > 3 tin → Báo lỗi "Tối đa 3 phòng".</td>
  <td>Bảng so sánh hiển thị.</td>
</tr>

<tr>
  <td class="id">UC-A3.5</td>
  <td>Báo cáo tin sai</td>
  <td class="actor">User</td>
  <td>Báo cáo tin sai/lừa đảo cho Admin.</td>
  <td>Đã đăng nhập.</td>
  <td class="flow">1. Bấm "Báo cáo".<br>2. Chọn lý do: Sai giá / Tin cũ / Lừa đảo / Khác.<br>3. Nhập ghi chú (tùy chọn).<br>4. Lưu vào bảng reports (status='pending').<br>5. Admin nhận thông báo.</td>
  <td class="flow">—</td>
  <td>Report được ghi nhận, Admin sẽ kiểm duyệt.</td>
</tr>

<tr>
  <td class="id">UC-A4.1</td>
  <td>Đăng tin nhà trọ (UGC)</td>
  <td class="actor">User</td>
  <td>Sinh viên tự đăng tin mới.</td>
  <td>Đã đăng nhập.</td>
  <td class="flow">1. Bấm "Đăng tin".<br>2. Điền: Tiêu đề, Giá, DT, Địa chỉ, Ảnh (≤10), Mô tả, Tiện ích.<br>3. Bấm "Đăng".<br>4. AI Risk Check tự động.<br>5a. Risk thấp → Đăng ngay (source='ugc').<br>5b. Risk cao → Chờ Admin duyệt.</td>
  <td class="flow">2a. Thiếu trường → Lỗi validate.<br>2b. Ảnh > 5MB → Yêu cầu nén.</td>
  <td>Tin được đăng hoặc chờ duyệt.</td>
</tr>

<tr>
  <td class="id">UC-A5.1</td>
  <td>Thông báo tin mới phù hợp</td>
  <td class="actor">User</td>
  <td>Push notification khi có tin mới khớp tiêu chí.</td>
  <td>Đã đăng nhập, có preference_vector.</td>
  <td class="flow">1. Crawler tìm tin mới.<br>2. So khớp với preference vector tất cả User.<br>3. Cosine Similarity > ngưỡng → Push notification / Email.<br>4. Nội dung: "[Tiêu đề], [Giá], [Khu vực]".</td>
  <td class="flow">—</td>
  <td>User nhận thông báo, click → trang chi tiết.</td>
</tr>

</table>

<!-- ═══════════════════════════════════ -->
<h2>NHÓM B — TÍNH NĂNG AI <span class="tag-ai">AI</span></h2>

<table>
<tr>
  <th style="width:7%">ID</th>
  <th style="width:10%">Tên UC</th>
  <th style="width:6%">Actor</th>
  <th style="width:12%">Mô tả</th>
  <th style="width:10%">Điều kiện tiên quyết</th>
  <th style="width:25%">Luồng chính</th>
  <th style="width:20%">Luồng thay thế / Ngoại lệ</th>
  <th style="width:10%">Điều kiện sau</th>
</tr>

<tr>
  <td class="id">UC-B1.1</td>
  <td>Onboarding Quiz</td>
  <td class="actor">User</td>
  <td>3 câu hỏi nhanh khi đăng ký để tạo preference vector.</td>
  <td>Vừa đăng ký xong / chưa điền quiz.</td>
  <td class="flow">1. Hiển thị 3 câu hỏi:<br>  Q1: Ngân sách? (Slider 500K–5M).<br>  Q2: Khoảng cách max CTU? (500m–5km).<br>  Q3: Tiện ích bắt buộc? (Checkbox).<br>2. Bấm "Hoàn tất".<br>3. Chuyển thành preference_vector → Lưu DB.</td>
  <td class="flow">1a. Bấm "Bỏ qua" → Dùng Popularity-Based thay AI.</td>
  <td>User có preference_vector, AI Recommendation hoạt động.</td>
</tr>

<tr>
  <td class="id">UC-B1.2</td>
  <td>Gợi ý "Dành cho bạn"</td>
  <td class="actor">User</td>
  <td>Top-10 phòng phù hợp nhất trên trang chủ.</td>
  <td>Đã đăng nhập, có preference_vector.</td>
  <td class="flow">1. User mở trang chủ.<br>2. Lấy preference_vector.<br>3. Cosine Similarity vs. tất cả listing (status='active').<br>4. Top-10 → Section "Dành cho bạn".</td>
  <td class="flow">2a. Chưa có vector → "Top phổ biến tuần này".</td>
  <td>Gợi ý cá nhân hiển thị. Extend: Tab "Khám phá" (80/20).</td>
</tr>

<tr>
  <td class="id">UC-B1.3</td>
  <td>Implicit Feedback</td>
  <td class="actor">System</td>
  <td>Thu thập hành vi ẩn để cập nhật vector người dùng.</td>
  <td>User đang duyệt tin.</td>
  <td class="flow">1. Ghi nhận: thời gian xem (> 30s), bookmark, click link nguồn, click SĐT.<br>2. Lưu vào bảng user_interactions.<br>3. Định kỳ cập nhật preference_vector dựa trên hành vi tích lũy.</td>
  <td class="flow">—</td>
  <td>Vector người dùng ngày càng chính xác hơn.</td>
</tr>

<tr>
  <td class="id">UC-B2.1</td>
  <td>Tìm bạn ở ghép</td>
  <td class="actor">User</td>
  <td>Matching bạn ghép dựa trên Forced Choice Survey.</td>
  <td>Đã đăng nhập + Đã điền hồ sơ.</td>
  <td class="flow">1. Bấm "Tìm bạn ghép".<br>2. Chưa có hồ sơ → Điền form tình huống (6 câu, Forced Choice).<br>3. Weighted Cosine Similarity vs. tất cả roommate_profiles.<br>4. Lọc Score ≥ 0.7.<br>5. Hiển thị: Avatar, Tên, Score (%), Tóm tắt.<br>6. "Gửi lời mời kết nối".</td>
  <td class="flow">4a. Không ai ≥ 0.7 → "Chưa có bạn ghép phù hợp, sẽ thông báo khi có người mới."</td>
  <td>Danh sách bạn ghép hiển thị / Lời mời được gửi.</td>
</tr>

<tr>
  <td class="id">UC-B3.1</td>
  <td>Chatbot hỏi đáp AI (RAG)</td>
  <td class="actor">User</td>
  <td>Hỏi bằng ngôn ngữ tự nhiên, trả lời từ dữ liệu thực (RAG).</td>
  <td>Đã đăng nhập. Vector DB đã index.</td>
  <td class="flow">1. Mở chatbot (góc phải dưới).<br>2. Nhập câu hỏi: "Phòng 1.5tr gần CTU?".<br>3. Nhúng câu hỏi → Vector (e5-small).<br>4. pgvector: Top-5 phòng + score.<br>5a. Score ≥ 0.65 → Prompt (context + POI) → Gemini → Trả lời + link phòng.<br>5b. Score &lt; 0.65 → "Không tìm thấy, thử tiêu chí khác" + link tìm kiếm.<br>6. Lưu Memory (5 lượt).</td>
  <td class="flow">2a. Câu hỏi ngoài domain → "Tôi chỉ hỗ trợ tìm nhà trọ."</td>
  <td>Câu trả lời + nguồn trích dẫn. Memory cập nhật multi-turn.</td>
</tr>

<tr>
  <td class="id">UC-B4.1</td>
  <td>Badge cảnh báo rủi ro</td>
  <td class="actor">Guest / User</td>
  <td>Mỗi tin hiển thị badge rủi ro AI tính tự động.</td>
  <td>Không.</td>
  <td class="flow">1. Hiển thị badge trên mỗi tin:<br>  ✅ An toàn (risk &lt; 0.3)<br>  ⚠️ Cần kiểm chứng (0.3–0.6)<br>  🔴 Nghi vấn (≥ 0.6)<br>2. Click badge → Popup lý do: "Giá thấp 40%", "Không có ảnh"...</td>
  <td class="flow">—</td>
  <td>Người dùng biết mức độ tin cậy của tin.</td>
</tr>

</table>

<!-- ═══════════════════════════════════ -->
<h2>NHÓM C — HỆ THỐNG & ADMIN <span class="tag-sys">System</span></h2>

<table>
<tr>
  <th style="width:7%">ID</th>
  <th style="width:10%">Tên UC</th>
  <th style="width:6%">Actor</th>
  <th style="width:12%">Mô tả</th>
  <th style="width:10%">Điều kiện tiên quyết</th>
  <th style="width:25%">Luồng chính</th>
  <th style="width:20%">Luồng thay thế / Ngoại lệ</th>
  <th style="width:10%">Điều kiện sau</th>
</tr>

<tr>
  <td class="id">UC-C1.1</td>
  <td>Crawl dữ liệu tự động</td>
  <td class="actor">System</td>
  <td>Crawler chạy định kỳ 6–12h lấy dữ liệu từ các trang nguồn.</td>
  <td>Cron job được cấu hình.</td>
  <td class="flow">1. Cron trigger (mỗi 6h).<br>2. Đọc nguồn + CSS selectors từ config JSON.<br>3. HTTP requests (1 req/5s, xoay User-Agent).<br>4. Parse HTML → Tiêu đề, Giá, DT, Địa chỉ, Ảnh.<br>5. NLP trích xuất tiện ích.<br>6. Geocoding đa tầng.<br>7. MinHash + LSH lọc trùng.<br>8. PostGIS tính khoảng cách POI.<br>9. AI Risk Check.<br>10. Nhúng vector RAG.<br>11. INSERT/UPDATE DB.</td>
  <td class="flow">3a. Bị block (403) → Log lỗi, alert Admin, bỏ qua nguồn.<br>4a. HTML đổi layout → Parser null → Log lỗi.</td>
  <td>DB cập nhật. Health check: &lt; 10 tin mới → Cảnh báo.</td>
</tr>

<tr>
  <td class="id">UC-C1.2</td>
  <td>Chuẩn hóa NLP & Geocoding</td>
  <td class="actor">System</td>
  <td>Trích xuất tiện ích + chuyển địa chỉ text → GPS.</td>
  <td>Có dữ liệu thô từ crawler.</td>
  <td class="flow">1. NLP parse mô tả → JSONB tiện ích.<br>2. Geocoding: Google API → Landmark fallback → Phường fallback.<br>3. Lưu geocode_confidence.</td>
  <td class="flow">2a. Geocode thất bại → confidence='failed', ẩn khỏi bản đồ.</td>
  <td>Dữ liệu được chuẩn hóa + có tọa độ.</td>
</tr>

<tr>
  <td class="id">UC-C1.5</td>
  <td>Tính khoảng cách POI (PostGIS)</td>
  <td class="actor">System</td>
  <td>Tính khoảng cách đến đồn CA, BV, trạm bus bằng PostGIS.</td>
  <td>Phòng trọ đã có tọa độ + bảng poi_locations đã seed.</td>
  <td class="flow">1. Với mỗi tin mới (có lat/lng).<br>2. PostGIS: ST_DistanceSphere() → distance_to_police, distance_to_hospital.<br>3. Cập nhật vào aggregated_listings.</td>
  <td class="flow">1a. Tin không có tọa độ → Bỏ qua, giá trị NULL.</td>
  <td>Các cột distance_to_* được điền.</td>
</tr>

<tr>
  <td class="id">UC-C2.1</td>
  <td>Dashboard tổng quan</td>
  <td class="actor">Admin</td>
  <td>Thống kê tổng quan hệ thống.</td>
  <td>Đăng nhập Admin.</td>
  <td class="flow">1. Truy cập /admin.<br>2. Hiển thị: Tổng tin (active/stale), Tin mới hôm nay, Tin bị report, Crawler status, Số user, Top phòng xem nhiều.</td>
  <td class="flow">—</td>
  <td>Dashboard hiển thị realtime.</td>
</tr>

<tr>
  <td class="id">UC-C2.2</td>
  <td>Kiểm duyệt tin flagged</td>
  <td class="actor">Admin</td>
  <td>Duyệt / Ẩn / Xóa tin bị cảnh báo rủi ro hoặc bị report.</td>
  <td>Có tin trong hàng chờ duyệt.</td>
  <td class="flow">1. Xem danh sách: risk cao + bị report.<br>2. Mỗi tin: Nội dung, Lý do flagged, Số report, Risk reasons.<br>3. Chọn: "Duyệt" / "Ẩn" / "Xóa vĩnh viễn".</td>
  <td class="flow">—</td>
  <td>Tin được xử lý, trạng thái cập nhật.</td>
</tr>

<tr>
  <td class="id">UC-C2.3</td>
  <td>Cấu hình Crawler</td>
  <td class="actor">Admin</td>
  <td>Bật/tắt nguồn, đổi tần suất, xem log.</td>
  <td>Đăng nhập Admin.</td>
  <td class="flow">1. Truy cập "Cấu hình Crawler".<br>2. Danh sách nguồn: Bật/Tắt toggle, Tần suất (dropdown), Log gần nhất.<br>3. Bấm "Lưu cấu hình".</td>
  <td class="flow">—</td>
  <td>Config crawler được cập nhật.</td>
</tr>

</table>

<!-- ═══════════════════════════════════ -->
<h2>BẢNG TÓM TẮT QUAN HỆ GIỮA CÁC USE CASE</h2>

<table>
<tr>
  <th>Quan hệ</th>
  <th>Use Case cơ sở</th>
  <th>Use Case liên quan</th>
  <th>Giải thích</th>
</tr>
<tr><td><strong>«include»</strong></td><td>UC-A2.1 (Tìm kiếm)</td><td>UC-A2.2 (Lọc), UC-A2.3 (Sắp xếp)</td><td>Tìm kiếm luôn bao gồm bộ lọc và sắp xếp.</td></tr>
<tr><td><strong>«include»</strong></td><td>UC-A3.1 (Chi tiết)</td><td>UC-B4.1 (Badge rủi ro)</td><td>Trang chi tiết luôn hiển thị badge.</td></tr>
<tr><td><strong>«include»</strong></td><td>UC-B1.2 (Gợi ý)</td><td>UC-B1.1 (Onboarding)</td><td>Gợi ý cần onboarding quiz trước.</td></tr>
<tr><td><strong>«include»</strong></td><td>UC-B2.1 (Matching)</td><td>UC-B2.1a (Hồ sơ ghép)</td><td>Matching cần có hồ sơ.</td></tr>
<tr><td><strong>«include»</strong></td><td>UC-A4.1 (Đăng tin)</td><td>UC-B4 (Risk Check)</td><td>Tin UGC luôn qua AI kiểm tra.</td></tr>
<tr><td><strong>«include»</strong></td><td>UC-C1.1 (Crawl)</td><td>UC-C1.2, C1.3, C1.5, C1.6</td><td>Crawl bao gồm toàn bộ pipeline.</td></tr>
<tr><td><strong>«extend»</strong></td><td>UC-A3.1 (Chi tiết)</td><td>UC-A3.2 (Yêu thích), UC-A3.5 (Báo cáo), UC-A3.4 (Chia sẻ)</td><td>Các hành động tùy chọn từ trang chi tiết.</td></tr>
<tr><td><strong>«extend»</strong></td><td>UC-B1.2 (Gợi ý)</td><td>UC-B1.4 (Khám phá 80/20)</td><td>Tab Explore là mở rộng tùy chọn.</td></tr>
</table>

<div class="footer">
  Tài liệu được tạo tự động bởi AI Agent · Đề tài THS2026-66 · ĐH Cần Thơ 2026
</div>

</body>
</html>"""

output_dir = r"d:\Dev\Workspaces\NCKH\Agent-Generated"

# Luôn tạo HTML
html_path = f"{output_dir}\\DacTa_UseCase.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)
print(f"✅ HTML created: {html_path}")

# Thử tạo PDF
if USE_WEASYPRINT:
    try:
        pdf_path = f"{output_dir}\\DacTa_UseCase.pdf"
        HTML(string=HTML_CONTENT).write_pdf(pdf_path)
        print(f"✅ PDF created: {pdf_path}")
    except Exception as e:
        print(f"❌ PDF failed: {e}")
        print("→ Vui lòng mở file HTML bằng trình duyệt và in ra PDF (Ctrl+P).")
else:
    print("→ Mở file HTML bằng trình duyệt và in ra PDF (Ctrl+P → Save as PDF).")
