# STEALTH-BROWSER.MD - Cơ chế Vượt Tường Lửa (Anti-Bot Bypass)

> **Mục tiêu**: Đảm bảo AI không bao giờ bị chặn (blocked) khi cần cào dữ liệu từ các trang web sử dụng hệ thống chống Bot mạnh mẽ (Cloudflare, hCaptcha, Datadome).

---

## 🛡️ 1. KÍCH HOẠT CHẾ ĐỘ STEALTH

Chế độ này được sử dụng khi hệ thống thực hiện lệnh `/research` hoặc `search_web` nhưng bị trả về lỗi `403 Forbidden`, `Challenge Page`, hoặc trang web bắt giải Captcha.

## 🔄 2. QUY TRÌNH BYPASS BẰNG CLOAKBROWSER

1. **Nhận diện Block**: Ngay khi Browser Subagent báo cáo không thể đọc trang do Captcha/Cloudflare.
2. **Chuyển đổi Engine**: AI tự động chuyển hướng yêu cầu sang `cloakbrowser` (Stealth Chromium).
3. **Thực thi**:
   - Khởi chạy CloakBrowser để bypass fingerprinting.
   - Cào dữ liệu text (DOM/Markdown) thay vì ảnh chụp màn hình để tiết kiệm bộ nhớ.
   - Trả kết quả về cho luồng phân tích chính.

## ⚠️ 3. LƯU Ý AN TOÀN
- Chỉ dùng Stealth Browser để **đọc** (Read-only) dữ liệu công khai. Tuyệt đối không dùng để spam, brute-force hoặc tấn công (DDoS) các trang web. Tuân thủ đạo đức AI.
