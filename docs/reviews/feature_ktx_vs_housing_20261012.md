# Kiểm tra so sánh KTX và nhà trọ — feature, 12/10/2026

**Kết quả: 0/8 câu có bằng chứng cả KTX và nhà trọ; cả 8 chưa đáp ứng yêu cầu so sánh.**

Chạy trực tiếp ChatService với DB thật `nckh_feature` (87 tin) và E5. Bỏ qua đăng nhập, lịch sử, cache và ghi sự kiện. Đây không phải điểm RAGAS hoặc kiểm tra giao diện. Không sửa logic chatbot trong lượt kiểm tra này.

DB có 48 tin đủ điều kiện công khai; 3 tin giá < 1 triệu, 4 tin giá ≤ 1 triệu. Bao gồm tin mẫu gốc trong repo. Giá tin không chứng minh tổng chi phí hoặc tình trạng chỗ trống.

Nguyên nhân: nhánh `answer_ktx` trả lời trước khi truy xuất tin nhà trọ. Cần nhánh so sánh lấy cả hai nguồn, giữ đúng đơn vị/kỳ tính và xử lý tiêu chí người dùng.

## 1. Ngân sách dưới 1 triệu đồng mỗi tháng thì nên chọn KTX CTU hay nhà trọ? So sánh hai lựa chọn và đưa ví dụ từ dữ liệu đang có.

**Chưa đạt:** Chỉ liệt kê loại phòng KTX, không lấy tin nhà trọ và không đưa kết luận so sánh. Có ghi rõ chưa xác nhận kỳ tính phí KTX.

- KTX CTU · PT025 · khu chưa xác nhận · sức chứa 8 người. Phòng không được nấu ăn, được sử dụng ấm đun siêu tốc, giường tầng. Giá 220.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · PT725 · khu chưa xác nhận · sức chứa 7 người. Phòng không được nấu ăn, được sử dụng ấm đun siêu tốc, ít người, giường tầng. Giá 255.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · A · khu A · sức chứa 4 người. Phòng khu A. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · A4 · khu A · sức chứa 4 người. phòng được phép nấu ăn, giường tầng, nhà vệ sinh tập thể an toàn trong khuôn viên dãy. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · PA425 · khu chưa xác nhận · sức chứa 4 người. Phòng được nấu ăn, giường tầng. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
Đang hiển thị 5/27 loại khớp; xem đầy đủ và lọc thêm trên trang KTX.
Ngân sách theo tháng không cùng kỳ tính với đơn giá đang có; chưa thể lọc theo ngân sách này hoặc kết luận mức phí tháng.
Danh mục loại phòng chưa xác nhận số chỗ trống hiện tại; cần kiểm tra với văn phòng KTX.

### Nguồn đã dùng

- [1] Danh mục loại phòng do người dùng cập nhật — danh mục người dùng cập nhật, không có URL công khai

## 2. Em có tổng cộng 1 triệu/tháng gồm tiền ở, điện, nước, wifi và gửi xe. KTX hay nhà trọ phù hợp hơn? Khoản nào chưa có dữ liệu thì nói rõ.

**Chưa đạt:** Có nêu điện nước và gửi xe KTX, nhưng thiếu chi phí nhà trọ; chưa đánh giá ngân sách tổng 1 triệu. Không được coi Wi-Fi là miễn phí chỉ vì phòng có Wi-Fi.

- Gửi xe: Xe đạp được miễn phí gửi xe. Trang hướng dẫn tân sinh viên 2026–2027 công bố xe máy/xe điện 25.000 đồng/sinh viên/tháng, nộp theo học kỳ. [1]
- Phí ở và đơn vị giá: Trang cơ sở vật chất CTU công bố khoảng 220.000–475.000 đồng/sinh viên/tháng, chưa gồm điện nước, đóng theo học kỳ. Trang không ghi ngày áp dụng. Phiếu đăng ký năm 2025 có phí/người/học kỳ 3,5 tháng. Các đơn giá trong danh mục người dùng cập nhật chưa xác nhận kỳ tính; không khẳng định là giá/tháng hay mức thu hiện hành. [2]
- Điện nước: Sinh viên nộp phí điện, nước hàng tháng theo lượng sử dụng thực tế của phòng; phí ở chưa bao gồm điện nước. [3]
- Wi-Fi và tiện ích: Phòng ở có Wi-Fi riêng từng phòng. Trong khuôn viên có căn tin, siêu thị mini; trang giới thiệu còn nêu nhà xe và khu vực giặt sấy. [1]

### Nguồn đã dùng

- [1] Hướng dẫn tân sinh viên đăng ký KTX · 2026–2027 — https://tansinhvien.ctu.edu.vn/sinh-hoat/huong-dan-tan-sinh-vien-dang-ky-o-ky-tuc-xa
- [2] Cơ sở vật chất KTX · Trung tâm Phục vụ Sinh viên — https://ssc.ctu.edu.vn/hoat/160-cs1.html
- [3] Thông báo 307/TB-CTSV · HKI 2026–2027 — https://ssc.ctu.edu.vn/images/upload/thong_bao/072026_tb_dk1_2627.pdf

## 3. Dưới 1 triệu/tháng, em muốn tự nấu ăn và có nhà vệ sinh riêng. Nên chọn KTX hay nhà trọ? Có lựa chọn nào đáp ứng được không?

**Chưa đạt:** Có lọc nấu ăn nhưng liệt kê A4 có nhà vệ sinh tập thể, chưa xử lý điều kiện nhà vệ sinh riêng và thiếu ví dụ nhà trọ.

- KTX CTU · A4 · khu A · sức chứa 4 người. phòng được phép nấu ăn, giường tầng, nhà vệ sinh tập thể an toàn trong khuôn viên dãy. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · PA425 · khu chưa xác nhận · sức chứa 4 người. Phòng được nấu ăn, giường tầng. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · A8 · khu A · sức chứa 8 người. phòng 8 người, giường bộ, nấu ăn. Giá 375.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · PA825 · khu chưa xác nhận · sức chứa 8 người. Phòng được nấu ăn, giường tầng. Giá 375.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · A6 · khu A · sức chứa 6 người. phòng 6 người, giường bộ, nấu ăn. Giá 395.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
Đang hiển thị 5/17 loại khớp; xem đầy đủ và lọc thêm trên trang KTX.
Ngân sách theo tháng không cùng kỳ tính với đơn giá đang có; chưa thể lọc theo ngân sách này hoặc kết luận mức phí tháng.
Danh mục loại phòng chưa xác nhận số chỗ trống hiện tại; cần kiểm tra với văn phòng KTX.

### Nguồn đã dùng

- [1] Danh mục loại phòng do người dùng cập nhật — danh mục người dùng cập nhật, không có URL công khai

## 4. Nhóm em 4 người, mỗi người dưới 1 triệu/tháng. So sánh ở KTX A4 với thuê chung nhà trọ, ghi rõ giá theo người hay theo phòng và kỳ tính giá.

**Chưa đạt:** Chỉ trả thông tin A4; thiếu ví dụ thuê chung nhà trọ và phép tính theo người. Không thể đổi phí KTX sang tháng khi kỳ tính chưa xác nhận.

- KTX CTU · A4 · khu A · sức chứa 4 người. phòng được phép nấu ăn, giường tầng, nhà vệ sinh tập thể an toàn trong khuôn viên dãy. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
Ngân sách theo tháng không cùng kỳ tính với đơn giá đang có; chưa thể lọc theo ngân sách này hoặc kết luận mức phí tháng.
Danh mục loại phòng chưa xác nhận số chỗ trống hiện tại; cần kiểm tra với văn phòng KTX.

### Nguồn đã dùng

- [1] Danh mục loại phòng do người dùng cập nhật — danh mục người dùng cập nhật, không có URL công khai

## 5. Em muốn ở một mình, yên tĩnh và riêng tư, ngân sách dưới 1 triệu/tháng. So sánh KTX và nhà trọ rồi tư vấn phương án phù hợp.

**Chưa đạt:** Người dùng muốn ở một mình nhưng trả danh sách KTX 4–8 người; không nhận diện xung đột nhu cầu hoặc so sánh nhà trọ.

- KTX CTU · PT025 · khu chưa xác nhận · sức chứa 8 người. Phòng không được nấu ăn, được sử dụng ấm đun siêu tốc, giường tầng. Giá 220.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · PT725 · khu chưa xác nhận · sức chứa 7 người. Phòng không được nấu ăn, được sử dụng ấm đun siêu tốc, ít người, giường tầng. Giá 255.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · A · khu A · sức chứa 4 người. Phòng khu A. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · A4 · khu A · sức chứa 4 người. phòng được phép nấu ăn, giường tầng, nhà vệ sinh tập thể an toàn trong khuôn viên dãy. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · PA425 · khu chưa xác nhận · sức chứa 4 người. Phòng được nấu ăn, giường tầng. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
Đang hiển thị 5/27 loại khớp; xem đầy đủ và lọc thêm trên trang KTX.
Ngân sách theo tháng không cùng kỳ tính với đơn giá đang có; chưa thể lọc theo ngân sách này hoặc kết luận mức phí tháng.
Danh mục loại phòng chưa xác nhận số chỗ trống hiện tại; cần kiểm tra với văn phòng KTX.

### Nguồn đã dùng

- [1] Danh mục loại phòng do người dùng cập nhật — danh mục người dùng cập nhật, không có URL công khai

## 6. KTX CTU và nhà trọ dưới 1 triệu thì bên nào an toàn hơn? Có đủ bằng chứng để kết luận không, và cần kiểm tra gì trước khi chọn?

**Chưa đạt:** Trả danh sách phòng thay vì phân tích bằng chứng an toàn, giới hạn dữ liệu và các bước kiểm tra.

- KTX CTU · PT025 · khu chưa xác nhận · sức chứa 8 người. Phòng không được nấu ăn, được sử dụng ấm đun siêu tốc, giường tầng. Giá 220.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · PT725 · khu chưa xác nhận · sức chứa 7 người. Phòng không được nấu ăn, được sử dụng ấm đun siêu tốc, ít người, giường tầng. Giá 255.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · A · khu A · sức chứa 4 người. Phòng khu A. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · A4 · khu A · sức chứa 4 người. phòng được phép nấu ăn, giường tầng, nhà vệ sinh tập thể an toàn trong khuôn viên dãy. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
- KTX CTU · PA425 · khu chưa xác nhận · sức chứa 4 người. Phòng được nấu ăn, giường tầng. Giá 285.000 đồng/người · chưa xác nhận kỳ tính giá. Đơn giá/người theo danh mục cập nhật; chưa xác nhận kỳ tính giá và thời hạn áp dụng. [1]
Đang hiển thị 5/27 loại khớp; xem đầy đủ và lọc thêm trên trang KTX.
Danh mục loại phòng chưa xác nhận số chỗ trống hiện tại; cần kiểm tra với văn phòng KTX.

### Nguồn đã dùng

- [1] Danh mục loại phòng do người dùng cập nhật — danh mục người dùng cập nhật, không có URL công khai

## 7. Em học ở khu II CTU, ngân sách dưới 1 triệu/tháng. So sánh vị trí KTX khu A/B với nhà trọ gần trường trong dữ liệu hiện có.

**Chưa đạt:** Chỉ trả tọa độ khu A, bỏ khu B trong cách viết A/B và không truy xuất vị trí nhà trọ để so sánh. Không có thời gian đi lại đã xác minh.

- Ký túc xá khu A: 10.0338798, 105.7702172 — Văn phòng phục vụ sinh viên KTX khu A. Điểm đại diện từ OpenStreetMap; chưa xác nhận cổng vào hoặc vị trí từng phòng. [1]
Bạn có thể mở vị trí và chỉ đường trên trang KTX của hệ thống.

### Nguồn đã dùng

- [1] Văn phòng phục vụ sinh viên KTX khu A · OpenStreetMap — https://www.openstreetmap.org/way/89864434

## 8. Nếu muốn chuyển vào ngay tuần này, dưới 1 triệu/tháng nên chọn KTX hay nhà trọ? Chỗ nào chắc chắn còn phòng?

**Chưa đạt:** Đúng khi không khẳng định KTX còn chỗ, nhưng bỏ phần nhà trọ và chưa đưa hướng lựa chọn có điều kiện. Tin trong DB không xác nhận chỗ trống hiện tại.

- Danh mục loại phòng, hình ảnh và tọa độ khu KTX không xác nhận số chỗ còn trống. Phải xem tình trạng trên Hệ thống Quản lý KTX hoặc liên hệ văn phòng để xác nhận tại thời điểm đăng ký. [1]
- Email KTX: ktx@ctu.edu.vn. Văn phòng khu A: 0292 3872 178; khu B: 0292 3872 275, theo thông báo 2026–2027. Một biểu mẫu cũ ghi số khu A khác; ưu tiên số trong thông báo mới. [1]

### Nguồn đã dùng

- [1] Thông báo 307/TB-CTSV · HKI 2026–2027 — https://ssc.ctu.edu.vn/images/upload/thong_bao/072026_tb_dk1_2627.pdf

