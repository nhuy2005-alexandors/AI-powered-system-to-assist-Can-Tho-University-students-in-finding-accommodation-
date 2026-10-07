# Đo rerank và rà soát gợi ý phòng trọ

Ngày đo: 07/10/2026. Máy local: Intel Core i5-12450HX, RAM 16 GB, Windows, PyTorch 2.5.1 CPU, 8 luồng intra-op. Dataset PostgreSQL: 789 tin, 788 vector E5. Model đã có trong cache Hugging Face; chạy offline để không tính thời gian tải mạng.

## Thay đổi đã giữ

- Giữ 50 ứng viên cosine, giới hạn 512 token/cặp, batch 2; không đổi model hoặc vector phòng.
- Gom các cặp nhu cầu/phòng theo độ dài token trước khi chạy BGE để giảm phần padding. Gắn điểm lại đúng phòng, xếp giảm dần theo điểm, dùng hạng cosine khi bằng điểm.
- Lưu tạm điểm BGE trong RAM: tối đa 1.024 cặp, hết hạn sau 300 giây. Khóa là SHA-256 của model, giới hạn token, nhu cầu/quận và toàn bộ văn bản phòng dùng để chấm điểm. Cache không chứa token đăng nhập, response API hoặc hồ sơ người dùng.
- Mỗi request vẫn đọc hồ sơ hành vi, loại phòng không quan tâm và lọc PostgreSQL. Thay đổi ngân sách, trạng thái phòng hoặc hành vi không lấy lại danh sách cũ từ cache; chỉ tái sử dụng điểm của các cặp còn phù hợp.
- Cache riêng từng worker và mất khi restart. Thay đổi nội dung phòng/nhu cầu tạo khóa mới. Hết hạn hoặc hết chỗ sẽ tính lại.

Không cần migration PostgreSQL/MongoDB, không cần embed lại dataset. API và schema response giữ nguyên.

## So sánh tính điểm chưa có cache

Script đọc dữ liệu thật, tạo vector từ ba nhu cầu cố định, lấy cùng 50 ứng viên rồi so sánh cách chia batch. Thời gian bên dưới gồm tokenization và suy luận BGE; tách riêng tải model, embed E5 và truy vấn SQL. Không dùng hồ sơ hành vi cho phép so sánh này.

| Nhu cầu | Batch cũ, theo hạng cosine | Gom theo độ dài, batch 2 | Thứ tự top 10 |
|---|---:|---:|---|
| Máy lạnh, vệ sinh riêng, gần ĐH Cần Thơ; tối đa 3 triệu | 45,851 s | 23,515 s | Giữ nguyên 10/10 |
| Có gác, chỗ nấu ăn riêng, sinh viên; tối đa 2 triệu | 25,432 s | 22,256 s | Giữ nguyên 10/10 |
| Nội thất, máy lạnh, chỗ để xe; tối đa 3 triệu, Ninh Kiều | 26,154 s | 22,992 s | Giữ nguyên 10/10 |

Đây là phép đo thăm dò, một lượt cho mỗi cấu hình/nhu cầu; chưa phải kiểm thử tải hoặc số đo p95. Baseline của nhu cầu đầu chạy ngay sau tải model nên có thể chịu chi phí khởi tạo suy luận; không dùng mức giảm 48,7% của lượt đó làm cam kết tốc độ. Hai nhu cầu tiếp theo giảm khoảng 12%. Sai khác điểm top 10 dưới 0,000003, thứ tự giữ nguyên ở cả ba nhu cầu. Batch 4 không nhanh hơn nhất quán, nên giữ batch 2.

Nguồn số đo và ID/điểm từng phòng: [recommendation_cpu_comparison.json](recommendation_cpu_comparison.json). Model BGE tải từ cache trong 1,609 s ở tiến trình benchmark; không bao gồm download lần đầu trên máy mới.

### Vì sao bỏ bản thử 20 ứng viên/384 token?

Lượt thử đầu chạy 12,287 s, nhưng chỉ còn 7/10 ID so với top 10 của cấu hình 50 ứng viên. Phòng 1015, mô tả có máy lạnh và gần ĐH Cần Thơ khu 1, đứng thứ 2 sau BGE ở tập 50 nhưng bị loại khỏi tập 20 từ bước cosine. Ba cặp cũng bị cắt ở mức 384 token. Không giữ thay đổi này chỉ để lấy thời gian thấp hơn.

Số đo thăm dò: [recommendation_cpu_screening.json](recommendation_cpu_screening.json). Baseline của lượt thăm dò chạy trong lúc dừng API cũ để giải phóng RAM, nên không dùng nó làm phép so sánh hiệu năng chính.

## API thực tế sau khởi động lại

Full API tại `http://127.0.0.1:8000`, dùng tài khoản thử nghiệm đã có nhu cầu và lịch sử. Hồ sơ vẫn ở phiên bản 3 trước/sau phép đo. Không ghi thêm hành vi hoặc sửa nhu cầu.

| Lượt GET `/recommend/for-you?top_k=10&rerank=true` | HTTP từ client local | `elapsed_ms` API |
|---|---:|---:|
| Đầu tiên, BGE chưa nạp trong API | 26.019 ms | 25.991 ms |
| Điểm đã có cache, lượt 1 | 78 ms | 43 ms |
| Điểm đã có cache, lượt 2 | 70 ms | 38 ms |
| Điểm đã có cache, lượt 3 | 90 ms | 65 ms |

Tất cả trả HTTP 200, lấy 50 ứng viên, trả 10 phòng có điểm BGE, đúng giới hạn giá và cùng thứ tự. Hồ sơ hành vi làm tập ứng viên khác benchmark nhu cầu thuần văn bản, vì vậy ID giữa hai phép đo không nhất thiết giống nhau.

Ngoài ra: health 200, preferences 200, cosine 200; cosine trả 10/542 phòng đủ điều kiện, HTTP 118 ms. Đã đối chiếu ID/tên/giá của 10 phòng cosine với `GET /listings/{id}`: khớp 10/10.

Nguồn: [recommendation_api_check.json](recommendation_api_check.json). Cache chỉ giúp khi gặp lại cùng cặp nhu cầu/phòng; không thể suy ra mọi request mới đều dưới 100 ms. Khi hết hạn 5 phút, nhu cầu mới hoặc restart, CPU vẫn có thể cần hàng chục giây. Một worker xử lý suy luận tuần tự, nên nhiều request mới đồng thời có thể phải xếp hàng.

## Rà soát độ phù hợp

Đã đọc mô tả của top 5 mỗi nhu cầu trong phép so sánh. Đây là kiểm tra bằng chứng trong tin đăng do người bán cung cấp, không xác minh thực địa, không phải bộ nhãn người dùng độc lập.

| Nhu cầu | Bằng chứng phù hợp | Điểm chưa đạt/chưa đủ dữ liệu |
|---|---|---|
| Máy lạnh, WC riêng, gần CTU | 1015 và 1322 nêu máy lạnh, gần ĐH Cần Thơ | 1154 đứng đầu nêu WC trong phòng và máy lạnh nhưng gần ĐH Tây Đô; 1345/947 nêu ĐH Nam Cần Thơ. Chưa bảo đảm đúng trường hoặc khoảng cách. |
| Gác, chỗ nấu ăn, sinh viên | 985 có gác, kệ bếp; 1195 có gác, bếp và hướng tới sinh viên | 1334 đứng đầu có gác nhưng mô tả không nêu chỗ nấu ăn. Không nên coi thông tin vắng mặt là tiện ích đã có. |
| Nội thất, máy lạnh, chỗ xe, Ninh Kiều | 1331 có máy lạnh và chỗ xe; 1390 có máy lạnh và nhà xe riêng | 957/1094/1077 nêu nội thất và máy lạnh nhưng chưa có bằng chứng rõ về chỗ để xe trong mô tả đã đọc. |

30/30 kết quả top 10 ở cấu hình chọn thỏa ngân sách đã nhập. Mức trùng thứ tự 10/10 trước/sau tối ưu chỉ xác nhận độ ổn định, không phải “độ chính xác 100%”. Chưa có đủ nhãn để kết luận đạt Precision@10 hoặc NDCG@10 của đề tài.

Bước đánh giá chất lượng tiếp theo của nhóm: gán nhãn mức phù hợp trên các nhu cầu đại diện, chỉ rõ cơ sở/cổng CTU cần đến, kiểm tra tọa độ và dùng điều kiện khoảng cách có cấu trúc. Không lấy việc tin chỉ nhắc một trường khác làm bằng chứng phòng xa CTU. Các giới hạn này tồn tại ở cả cấu hình cũ và mới; lần tối ưu hiệu năng này không thay đổi cách hiểu địa điểm.

## Chạy lại

Từ thư mục gốc, PostgreSQL handoff local tại `127.0.0.1:5454` và hai model đã được tải:

```powershell
.\apps\api\.venv\Scripts\python.exe scripts/benchmark_recommendation.py --offline --repeats 2 --output eval/reports/recommendation_cpu_rerun.json
```

Script hỏi mật khẩu PostgreSQL qua `getpass`, không ghi vào report. Có thể đặt `RECOMMENDATION_BENCHMARK_DATABASE_URL` trong môi trường của tiến trình nếu dùng catalog khác. Không commit URL chứa mật khẩu. Bỏ `--offline` nếu máy cần tải model lần đầu; thời gian tải model được ghi riêng.

Muốn so sánh thêm cấu hình thử:

```powershell
.\apps\api\.venv\Scripts\python.exe scripts/benchmark_recommendation.py --offline --cases 1 --variants baseline initial_tuning four_threads full_length sorted_batch2 sorted_batch4 --output eval/reports/recommendation_cpu_variants.json
```

Đo riêng lúc không có tiến trình khác chạy model. Script đọc dữ liệu, không ghi vector hay hồ sơ. Nó ghi report sau mỗi lượt; console báo bắt đầu/kết thúc để theo dõi tiến độ.

## Kiểm thử hồi quy

```powershell
$env:RECOMMENDATION_TEST_MONGO_URI = 'mongodb://127.0.0.1:27018/'
.\apps\api\.venv\Scripts\python.exe -m pytest apps/api/tests/test_recommendation_behavior.py apps/api/tests/test_recommendation_mongo.py apps/api/tests/test_recommendation_models.py -q
```

Kết quả: **66 passed**. Kiểm thử Mongo dùng database tạm riêng. Kiểm thử model dùng bộ giả lập để kiểm tra gắn điểm đúng phòng, cache hết hạn/giới hạn dung lượng, đổi nhu cầu/giá, loại ứng viên, cảnh báo cắt token và từ chối điểm không hợp lệ. Suy luận thật được xác nhận bằng các phép đo ở trên. Có một cảnh báo deprecation của Starlette/AnyIO, không làm thất bại kiểm thử.
