# Tích hợp KTX vào feature/ghep-ban-chat — 12/10/2026

## Rà soát

Feature thiếu trang KTX, ảnh, lớp GPS và danh mục cấu trúc cho chatbot. Đã bổ sung từ bản xem trước. Bản đồ giữ MapLibre, các cụm tin, POI, chỉ đường. Chatbot giữ tại `/tro-ly`; `/chat` tiếp tục là nhắn tin ghép bạn. Giữ toàn bộ code ghép bạn, nhắn tin, đánh giá và quản trị đã có.

## Dữ liệu và cấu hình

- 43 loại phòng, 2 khu A/B, 14 ảnh gốc CTU; 107 bản ghi E5 384 chiều dùng chung giữa trang và chatbot.
- Migration feature là **103_ctu_dormitories.sql**, tránh trùng migration 102_reviews_sentiment.sql. Không đổi thứ tự khởi tạo DB riêng của feature.
- Kỳ tính giá chưa xác nhận được giữ nguyên; dữ liệu phí CTU 2025 ghi theo học kỳ 3,5 tháng. GPS là điểm đại diện, không khẳng định cổng/phòng. Không có dữ liệu chỗ trống trực tiếp.
- Gemini dùng khóa proxy riêng trong `.env` bị Git bỏ qua. Giữ cấu hình và JWT đang chạy. Không ghi khóa vào báo cáo.
- Cache câu trả lời chứa hash danh mục và endpoint để cập nhật dữ liệu/cấu hình làm hết hiệu lực cache cũ. Câu khẩn cấp giữ ưu tiên trước xử lý KTX.

## Khởi động

```powershell
cd "D:\feature-ghep-ban-chat"
docker compose up -d --build db redis api web
docker compose --profile tools run --rm ktx-indexer
```

Mở http://localhost:3000/ktx ; http://localhost:3000/map?dormitory=A ; http://localhost:3000/tro-ly . Bật dịch vụ proxy cổng 8317 để dùng Gemini.

## Báo cáo RAGAS

Giữ nguyên 58 câu gốc, thêm tám câu KTX (66 câu). Bản báo cáo 48 câu pháp lý/KTX ngày 12/10 ở `docs/reviews/legal_ktx_proxy_20261012.html` được sao chép nguyên trạng từ bản xem trước cổng 3001. **Đây không phải kết quả chấm lại bản feature.** Manifest giữ hash và cấu hình gốc. Không dùng điểm cũ để kết luận chất lượng toàn bộ bản feature. Có thể mở tại http://localhost:3000/reviews/legal_ktx_proxy_20261012.html .

## Sao lưu

Các file tồn tại trước tích hợp được lưu dưới `.local-backups/ktx-integration-20261012/`. DB được sao lưu trước khi thêm bảng KTX. Không xóa volume, tài khoản, tin trọ, lịch sử hoặc corpus pháp luật.

## Kết quả kiểm tra tích hợp

- Build giao diện Next.js thành công, kiểm tra kiểu dữ liệu đạt.
- 90 kiểm thử KTX/chatbot/proxy đạt; 34 kiểm thử thuật toán ghép bạn đạt (17 ca API không được chạy trong lượt này).
- Bốn câu KTX chạy với repository và E5 thật: A4, tọa độ A/B, chỗ trống A4, người thân/người ngoài ở qua đêm. Đều có nguồn và ngữ cảnh, không degraded. Lưu câu trả lời tại `docs/reviews/feature_ktx_smoke_20261012.json`.
- Proxy trả danh sách model HTTP 200; kiểm tra sinh JSON `ok=true` thành công.
- Kiểm tra trình duyệt: trang KTX hiện thông tin/ảnh/bộ lọc; bản đồ MapLibre hiện marker KTX A/B, popup có nguồn và chỉ đường. Liên kết hỏi AI dùng `/tro-ly`.
- Đã sửa phát hiện khi review: câu “KTX đang cháy” được chuyển sang nhánh khẩn cấp; câu hỏi phòng cháy thông thường và “đang chạy xe” vẫn không bị hiểu thành khẩn cấp.

## Bộ 87 tin đã chọn và đang chạy

Người dùng đã xác nhận dùng bộ có sẵn trong repo feature: **82 tin cào + 5 tin mẫu = 87 tin**. API đang dùng DB riêng `nckh_feature`, không nhập bộ 789 tin. ID đúng 1–5 và 1001–1082, giữ nguyên nội dung và trạng thái seed. Cào tự động đã tắt bằng `CRAWLER_ENABLED=false`; mặc định Compose cũng tắt.

Theo bộ lọc hiện có của feature, **48 tin hiển thị công khai**; các dòng còn lại thuộc loại nhà/mặt bằng hoặc chưa đạt điều kiện làm sạch. Không thay trạng thái để ép đủ 87 tin lên trang. Bản đồ vẫn dùng bộ lọc và tọa độ của feature, thêm riêng hai điểm KTX A/B.

Giữ 84 tài khoản, dữ liệu ghép bạn/nhắn tin và corpus pháp luật `legal_ctu_v1` (45 văn bản, 571 đoạn). KTX giữ 107 vector. Cache trả lời cũ hết hạn, lịch sử hội thoại được giữ. Một dòng lịch sử đánh giá rủi ro gắn với bộ tin cũ được giữ ở DB gốc và bản sao lưu.

DB gốc `nckh` giữ nguyên **990 tin** tại thời điểm tách (tác vụ cào cũ đã thêm một dòng sau lần kiểm tra 989 tin; đã dừng trước khi tách). Không xóa volume. Bản sao lưu đầy đủ nằm tại `.local-backups/ktx-integration-20261012/database-before-feature-87.dump`.

Khi tạo volume mới, Docker tự nạp cả 5 tin mẫu và 82 tin cào. Với volume đang có, init script không chạy lại; cấu hình máy hiện tại đã trỏ DB riêng. Không chạy lại file COPY seed lên DB đã có dữ liệu.

Biên bản số lượng, hash seed và kiểm tra HTTP: `docs/reviews/feature_87_dataset_20261012.json`. Bốn câu KTX đã chạy lại với DB riêng trong `feature_ktx_smoke_20261012.json`.
