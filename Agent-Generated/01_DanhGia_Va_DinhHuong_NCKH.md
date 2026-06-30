# 📑 TÀI LIỆU 1: ĐÁNH GIÁ VÀ ĐỊNH HƯỚNG ĐỀ TÀI NCKH
**Đề tài:** Xây dựng hệ thống tổng hợp và gợi ý nhà trọ ứng dụng AI hỗ trợ sinh viên ĐH Cần Thơ (THS2026-66)

---

## 1. 🔍 ĐÁNH GIÁ TÌNH TRẠNG ĐỀ TÀI (Dựa trên Thuyết minh v2)

### Điểm mạnh đã đạt được:
- **Tính thực tiễn cao:** Bài toán tìm trọ của sinh viên CTU là một nhu cầu lớn, có thật và cấp thiết.
- **Phạm vi hợp lý:** Khoanh vùng sinh viên CTU và khu vực Ninh Kiều, loại trừ các vấn đề pháp lý hợp đồng.
- **Tính pháp lý đúng đắn:** Đã xác định đúng "Lĩnh vực Khoa học Kỹ thuật và Công nghệ" và loại hình "Nghiên cứu ứng dụng".
- **Tiến độ & Phân công:** Kế hoạch 6 tháng (5/2026 – 10/2026) được tổ chức chạy song song với sự phân công "Thành viên chính" rõ ràng.

### Khuyết điểm cần khắc phục:
1. **Thiếu tài liệu khoa học có chỉ số:** Tổng quan tài liệu hiện tại chủ yếu là bài báo chí. Cần bổ sung các bài báo khoa học (Scopus/ISI/Tạp chí trong nước) về Recommendation Systems, AI trong bất động sản.
2. **Thuật toán AI chưa cụ thể:** Cần chỉ đích danh thuật toán (VD: Content-Based Filtering, RAG LLM) thay vì nói chung chung là "thuật toán gợi ý".

---

## 2. ⚠️ BÀI TOÁN DỮ LIỆU: NGHỊCH LÝ "CHICKEN-AND-EGG"

Hệ thống AI chỉ gợi ý tốt khi có **dữ liệu chính xác và cập nhật (Real-time / Freshness)**. 
Tuy nhiên, nếu hệ thống bỏ actor "Chủ trọ" và hoạt động như trang rao vặt, chúng ta gặp bài toán con gà - quả trứng:
- Không có user đăng tin → Không có dữ liệu nhà trọ → AI không thể gợi ý → Sinh viên không dùng hệ thống → Không có user.

### Giới hạn của các nguồn dữ liệu truyền thống:
- **User tự đăng (UGC):** Khó lôi kéo người dùng mới khi hệ thống chưa có ai.
- **Google Maps API:** Chỉ có tọa độ và tên, không có giá, diện tích, hình ảnh để AI làm việc.
- **Khảo sát thực địa:** Mất thời gian, dữ liệu bị "chết" và lỗi thời chỉ sau 1 tháng.

---

## 3. 🎯 ĐỊNH HƯỚNG GIẢI QUYẾT: MÔ HÌNH "AI AGGREGATOR"

Để giải quyết bài toán dữ liệu, đề tài cần chuyển dịch từ mô hình "Sàn giao dịch/Marketplace" (cũ) sang mô hình **Bộ tổng hợp thông minh (AI-Powered Aggregator)** kết hợp **Xác thực cộng đồng (Community Verification)**.

### Cơ chế hoạt động:
1. **Thu thập (80% dữ liệu):** Tự động Crawl metadata từ nhiều nguồn có sẵn (Phongtro123, Chotot, Mogi). 
2. **Làm giàu dữ liệu (AI):** Dùng AI/NLP để chuẩn hóa mô tả, trích xuất tiện ích, phát hiện tin trùng lặp, tính điểm rủi ro.
3. **Phục vụ:** Hiển thị kết quả cho sinh viên, kèm theo các công cụ AI (Gợi ý cá nhân hóa, Matching bạn ghép, Chatbot RAG).
4. **Xác nhận (20% dữ liệu):** Cộng đồng sinh viên tham gia báo cáo "phòng đã cho thuê", review phòng thực tế.
5. **Đạo đức & Pháp lý:** Không lưu trữ tin gốc, chỉ hiển thị thông tin tóm tắt và **DẪN LINK VỀ TRANG GỐC** (giống mô hình Trivago, Google).

### Đánh giá mô hình mới:
| Tiêu chí | Điểm | Nhận xét |
|---|---|---|
| Dữ liệu ngày đầu | ✅ Tốt | Crawl xong là có hàng ngàn tin, AI có thể hoạt động ngay |
| Khả năng Real-time | ✅ Tốt | Crawler chạy định kỳ mỗi 6h, dữ liệu "chết" trên nguồn sẽ tự động bị ẩn |
| Rào cản kỹ thuật | ⚠️ Khá | Yêu cầu viết crawler, xử lý NLP, giải quyết Deduplication (lọc trùng lặp) |
| Giá trị khoa học | ⭐⭐⭐⭐⭐ | Mang đậm tính Khoa học Dữ liệu (Data Science), Data Engineering và AI. Cao hơn việc chỉ viết website CRUD. |

**Kết luận:** Hướng đi Aggregator là hoàn hảo cho một đề tài NCKH, giúp sinh viên tập trung vào phần lõi "Trí tuệ nhân tạo" và "Dữ liệu" thay vì phải đi làm marketing thu hút người dùng.
