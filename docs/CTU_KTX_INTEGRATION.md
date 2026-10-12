# KTX Đại học Cần Thơ — bản feature

Hướng dẫn tích hợp và giới hạn dữ liệu: [FEATURE_KTX_INTEGRATION_20261012.md](FEATURE_KTX_INTEGRATION_20261012.md).

## Dùng chung dữ liệu

Trang `/ktx`, lớp KTX trên bản đồ MapLibre `/map` và chatbot `/tro-ly` đọc cùng danh mục `public.ctu_ktx_catalog` và chỉ mục `public.ctu_ktx_search_documents`. API công khai `GET /ktx`, `GET /ktx/map`. GeoJSON dùng `[kinh độ, vĩ độ]`.

43 loại phòng, 2 khu, 16 thông tin chung, 46 điều/mục từ nguồn CTU; 107 vector E5 384 chiều. 14 ảnh gốc CTU tại `apps/web/public/images/ktx`, nguồn và hash trong `sources.json`.

27 loại phòng từ bảng cập nhật người dùng có giá/người nhưng chưa xác nhận kỳ tính. 16 loại từ phiếu CTU 2025 có giá/người/học kỳ 3,5 tháng; không khẳng định giá hiện hành. Mã PB không mặc nhiên thuộc khu B. GPS là điểm đại diện OSM; không có tình trạng chỗ trống trực tiếp.

## Bộ tin trọ

Bản feature hiện dùng `POSTGRES_DB=nckh_feature`: 87 tin gốc trong repo (82 cào + 5 mẫu), 48 tin đủ điều kiện hiển thị công khai. `CRAWLER_ENABLED=false`. DB cũ giữ nguyên. Xem biên bản `docs/reviews/feature_87_dataset_20261012.json`.

## Khởi động

```powershell
docker compose up -d --build db redis api web
docker compose --profile tools run --rm ktx-indexer
```

API và indexer cùng dùng cache model `models`. Migration **103** chỉ bổ sung hai bảng và chỉ mục KTX; không thay migration 102 của chức năng đánh giá.

## Sửa bảng loại phòng

Sửa `Data/student_housing/ktx_ctu_loai_phong_cap_nhat.csv`, giữ bốn cột. Sau đó:

```powershell
python scripts/prepare_ctu_ktx_catalog.py
docker compose --profile tools run --rm ktx-indexer
```

Kiểm tra checksum nguồn, vector hợp lệ và cập nhật danh mục/chỉ mục trong cùng giao dịch. Vector cùng nội dung/model được dùng lại. Cache trả lời hết hiệu lực khi hash danh mục hoặc endpoint thay đổi.

## Gemini proxy

Khóa thật chỉ nằm trong `.env` bị Git bỏ qua: `GEMINI_PROXY_API_KEY`. Khi có khóa proxy, các khóa Google được giữ nhưng không được luân phiên gửi sang proxy. Endpoint Docker: `GEMINI_DOCKER_BASE_URL`; endpoint Windows: `GEMINI_BASE_URL`.

## RAGAS

Ngân hàng 66 câu tại `eval/datasets/chatbot_question_bank.txt`. Báo cáo 48 câu đã chấm từ bản xem trước được giữ nguyên tại `docs/reviews/legal_ktx_proxy_20261012.html`; **không phải kết quả chấm lại feature**. Chạy lượt mới phải dùng tên JSON khác, tránh trộn pipeline/kho nguồn khác nhau:

```powershell
docker compose -f docker-compose.yml -f docker-compose.ktx-ragas.yml --profile evaluation run --rm --build ktx-evaluation --questions /eval/datasets/chatbot_question_bank.txt --output /eval/reports/feature_legal_ktx_new.json --phase all --exclude-categories find_listing --judge-provider gemini --judge-model gemini-3.8-flash-high --score-workers 2 --score-abstentions
```

Điểm RAGAS không chứng minh đúng luật/còn hiệu lực; chưa có đáp án chuẩn độc lập nên không báo Answer Correctness/Context Recall. Model qua alias proxy chưa xác minh model nền.

## Nhánh tư vấn và so sánh — 12/10/2026

`app/ktx/advice.py` xử lý `ktx_advice` và `ktx_comparison`, chạy sau ưu tiên khẩn cấp và trước tra cứu KTX/pháp luật thông thường. Câu pháp lý phối hợp các chủ đề khác vẫn đi luồng pháp luật. Nhánh tra cứu loại phòng/nội quy/đăng ký KTX được giữ.

So sánh dùng cùng DB danh mục KTX và bộ tin trọ đang hiển thị; kiểm tra ngân sách riêng tiền thuê/tổng chi, giá theo người/phòng, nhóm, nấu ăn, WC riêng, riêng tư, vị trí, an ninh và chỗ trống. Không quy đổi đơn giá KTX chưa rõ kỳ. Tin mẫu 1–5 vẫn được giữ trong DB 87 tin nhưng không dùng làm lựa chọn thuê thực tế. Thiếu xác nhận tiện nghi/sức chứa thì chỉ hiện ví dụ có điều kiện, đánh dấu `partial_answer`.

Câu trả lời được dựng từ trường dữ liệu có nguồn, không gọi model sinh văn bản cho nhánh này. Proxy Gemini của các nhánh cũ giữ nguyên. Cache dùng pipeline `feature-ktx-advice-v5`, xét cả phiên bản KTX và thay đổi tin trọ. Hỗ trợ nối tiếp đổi ngân sách, hỏi thêm nhà trọ và nấu ăn.

Kết quả: `docs/reviews/feature_ktx_vs_housing_after_20261012.html`. Tám câu so sánh có nguồn cả hai phía; bốn ca tư vấn/nối tiếp đạt; 104 kiểm thử đạt và 9 ca bỏ qua. Chưa chấm lại RAGAS hay xác minh giá/phòng trống trực tiếp. DB test riêng là `nckh_feature_test`.
