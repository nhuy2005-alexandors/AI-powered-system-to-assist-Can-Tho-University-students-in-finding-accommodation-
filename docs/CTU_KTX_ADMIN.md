# Quản lý KTX CTU

## Mở trang

Đăng nhập bằng tài khoản có vai trò admin, mở http://localhost:3000/admin/ktx hoặc chọn **Quản lý KTX** trong thanh bên.

## Dữ liệu có thể sửa

- Năm học: sao chép năm đang chọn để tạo năm mới; lưu trữ/khôi phục năm cũ. Tình trạng chỗ trống được xóa khi sao chép sang năm mới.
- Khu A/B: tên, mô tả, quy mô, liên hệ, ảnh bìa, GPS và nguồn tọa độ.
- Loại phòng: sức chứa, giá và kỳ tính, khu, nấu ăn, giường, vệ sinh, ghi chú và nguồn. Giá theo người; chỉ chọn tháng nếu đã xác nhận kỳ tính.
- Từng phòng: khu/dãy/số phòng, loại phòng, sức chứa, ghi chú, tình trạng và ngày ghi nhận. Không tự đồng bộ cổng CTU.
- Ảnh: tải JPG/PNG/WEBP tối đa 8 MB, 24 megapixel; thêm chú thích, nguồn và liên kết khu/phòng/loại phòng. Hệ thống bỏ EXIF, thu nhỏ tối đa 1920 px và lưu JPEG trong volume media. Gỡ ảnh khỏi bản nháp không xóa file của các năm khác.
- Thông tin tư vấn và nguồn dữ liệu: chỉnh nội dung, liên kết, chủ đề để chatbot tra cứu. Giữ các mục tư vấn cốt lõi và nguồn của điều khoản đã nhập.
- Lịch sử: người thao tác, loại thay đổi, thời điểm; giữ toàn bộ bản trước/sau trong bảng kiểm toán, giao diện hiển thị 20 thao tác gần nhất của năm.

## Lưu và công bố

**Lưu bản nháp** chỉ lưu trong năm đang sửa. **Công bố & dùng năm này** tạo các vector E5 thực cho phần nội dung thay đổi, rồi cập nhật danh mục công khai và chỉ mục trong cùng giao dịch. Trang KTX, bản đồ, chatbot dùng bản đã công bố. Mỗi thời điểm chỉ có một năm đang công bố; năm khác vẫn được giữ để xem và chỉnh sửa. Nếu embedding lỗi, giữ nguyên bản công bố và bản nháp. Không thể lưu trữ năm đang công bố.

Nếu người khác đã sửa trước, hệ thống yêu cầu tải lại để tránh ghi đè. Dữ liệu phòng là ghi nhận thủ công có ngày, không phải tồn phòng trực tiếp. Nội quy CTU gốc đã nhập được giữ trong chỉ mục; nếu có văn bản mới cần nhập nguồn mới riêng.

## Cài đặt và lưu trữ

Migration: `infra/db/migrations/104_ktx_admin.sql`. Các bảng mới: `ctu_ktx_years`, `ctu_ktx_admin_audit`; danh mục công khai vẫn ở `ctu_ktx_catalog` và vector ở `ctu_ktx_search_documents`. Migration được thêm vào image DB cho cài đặt mới; DB đang có cần áp dụng migration riêng trước khi chạy API mới.

Khi import danh mục gốc sau khi tạo DB mới, lần mở danh sách năm của admin sẽ khởi tạo năm 2026-2027 từ dữ liệu gốc nếu chưa có năm nào. Năm này chỉ là nhãn của danh mục hiện có; không xác nhận phí lịch sử 2025 áp dụng cho năm 2026-2027.

Sao lưu trước triển khai tại `.local-backups/ktx-admin-20261012/database-before-admin.dump`; ảnh tải lên nằm trong volume `nckh_media`. Sao lưu cả DB và volume ảnh. Bộ 87 tin nhà trọ không thay đổi.

## Danh mục phòng 2026 đã công bố

Ngày 12/10/2026, thay 43 loại phòng cũ bằng 27 loại phòng trong bảng do người dùng cung cấp. Đã bỏ nhóm phiếu CTU năm 2025 khỏi danh mục đang công bố; giá của 27 loại hiển thị theo người/học kỳ 3,5 tháng (2026). Xem `docs/reviews/ktx_2026_catalog_update_20261012.md` để đối chiếu mã và giá.
