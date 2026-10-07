# Bàn giao chức năng gợi ý phòng trọ

Người tổng hợp nhánh và người làm frontend đọc file này sau khi merge.
Nhánh bàn giao: `codex/goi-y-phong-tro`, tạo từ `feature/update-local`. Ghi nhận ngày 07/10/2026.

Người nhận nhánh muốn biết cần migrate gì và có phải embed lại không: đọc mục **4.0** trước, rồi chọn cách chạy ở 4.1 hoặc 4.2.

## 1. Chức năng hiện tại

Backend đã có:

- Nhận nhu cầu, tạo vector bằng E5, lọc giá/quận và xếp phòng theo cosine.
- Rerank bằng BGE khi gọi với `rerank=true`.
- Lưu nhu cầu và lịch sử tương tác trong MongoDB.
- Lấy tài khoản từ JWT của hệ thống auth hiện tại.
- Điều chỉnh vector sở thích từ xem/lưu/liên hệ và loại phòng không quan tâm.

Frontend cần làm form nhu cầu, danh sách “Dành cho bạn”, mở chi tiết phòng và gửi hành vi. Thiết kế theo Figma do người làm frontend phụ trách.

Đã kiểm tra trực tiếp API chung tại `http://127.0.0.1:8000` ngày 07/10/2026:

| Kiểm tra | Kết quả |
| --- | --- |
| Đăng nhập và đọc nhu cầu | Đúng hồ sơ của tài khoản thử nghiệm |
| `GET /recommend/preferences` | Ngân sách 3.000.000 VND; phiên bản 3; 1 phòng tham gia học; trọng số 5; hệ số trộn 0,25 |
| `GET /recommend/for-you?top_k=10&rerank=false` | 10 phòng từ 542 phòng đủ điều kiện; `elapsed_ms=52` |
| Chi tiết của cả 10 phòng | ID, tên và giá khớp với kết quả gợi ý |

Ví dụ: phòng `1310`, “Phòng trọ 1.6tr/tháng, có máy lạnh, ưu tiên sinh viên”, giá `1600000` ở cả API gợi ý và API chi tiết.

52 ms là thời gian xử lý API báo ở lần gọi đó, không phải thời gian tải toàn bộ trang. Kết quả xác nhận luồng API; độ phù hợp của gợi ý và tốc độ rerank cần đánh giá thêm.

## 2. Merge code và chuyển dữ liệu

Git mang theo các file đã commit. Dữ liệu phát sinh trên máy chạy được quản lý riêng.

| Thành phần | Đi theo merge? | Máy nhận cần làm |
| --- | --- | --- |
| Source, cấu hình mẫu, migration, scripts, tài liệu, kiểm thử | Có, sau khi commit/push | Merge và giữ phần tích hợp API chung |
| Document trong hai collection MongoDB | Không | Dùng cùng MongoDB hoặc khởi tạo/chuyển dữ liệu |
| Volume Docker chứa MongoDB | Không | Dựng Mongo trên máy nhận hoặc dùng dịch vụ chung |
| Phòng, vector và tài khoản PostgreSQL | Không | Dùng/import dữ liệu tương ứng |
| `.env`, mật khẩu, JWT secret | Không | Cấu hình riêng cho môi trường nhận |
| `.venv` và cache model E5/BGE | Không | Cài dependencies; chuẩn bị model |

**Bạn nhận nhánh dùng được hai collection này.** Nếu dùng MongoDB mới, script setup tạo đúng collection/index; người dùng lưu nhu cầu và tương tác sẽ tạo document mới. Collection mới chưa có lịch sử của máy cũ.

Trên cùng laptop, cùng MongoDB, cùng tên database và volume còn nguyên thì dữ liệu cũ vẫn dùng được. Trên máy khác, kết nối dịch vụ chung hoặc backup/restore dữ liệu nếu cần giữ lịch sử.

Runner hiện dùng PostgreSQL `localhost:5454/nckh_handoff`, tức database trên máy chạy. `localhost` trên bốn laptop là bốn máy khác nhau. Sửa schema hay tạo vector trên một máy chỉ tác động database đó. Cả nhóm thấy cùng thay đổi khi cùng kết nối một server/database; nếu mỗi người chạy database local thì cần áp dụng migration và nhận dữ liệu/vector trên từng máy.

Khi chuyển dữ liệu, giữ đúng quan hệ:

- `user_id="postgres:9"` ứng với `users.id=9` trong PostgreSQL đang chạy. ID 9 ở hai database tài khoản có thể thuộc hai người khác nhau.
- `listing_id=1310` trỏ đến `aggregated_listings.id=1310`. Import phòng rồi đổi ID sẽ làm lịch sử trỏ sai.
- Giữ cả vector phòng và `embedding_model` khi chuyển catalog.

Nếu chưa ánh xạ được tài khoản/phòng, dùng MongoDB riêng cho môi trường mới và cho người dùng nhập lại nhu cầu. Hồ sơ demo không cần chuyển để chức năng chạy được.

Nhánh này dùng tài khoản PostgreSQL và JWT của API chung. Nếu nhánh auth sau merge đổi sang tài khoản MongoDB, cần thay dependency xác thực recommendation bằng dependency đã kiểm tra token/tài khoản của nhóm, rồi trả khóa ổn định như `mongo:<users._id>`. Giữ hai collection recommendation được, nhưng phải ánh xạ hồ sơ nếu muốn giữ lịch sử; cấu hình hiện tại chưa tự hỗ trợ nguồn auth MongoDB.

Muốn giữ dữ liệu demo: backup/restore hai collection bằng MongoDB Database Tools hoặc cùng kết nối MongoDB đang có; dữ liệu phòng/tài khoản PostgreSQL bàn giao riêng. Archive database chứa hồ sơ/lịch sử, gửi riêng nếu nhóm cần và không đưa vào Git.

## 3. Hai collection và ý nghĩa các trường

| Nơi lưu | Nội dung |
| --- | --- |
| PostgreSQL `users`, `user_identities` | Tài khoản và danh tính đăng nhập |
| PostgreSQL `aggregated_listings` | ID, tên, giá, mô tả phòng, `embedding_vector` và metadata embedding |
| MongoDB `recommendation_profiles` | Nhu cầu và vector sở thích của mỗi tài khoản |
| MongoDB `recommendation_interactions` | Lịch sử xem/lưu/liên hệ/không quan tâm |

Hai collection MongoDB không chứa bản sao đầy đủ của phòng, tài khoản, mật khẩu hay token.

Schema PostgreSQL đã có `aggregated_listings.embedding_vector VECTOR(384)` và `users.preference_vector VECTOR(384)`. Module gợi ý hiện lấy vector phòng từ PostgreSQL, còn vector sở thích người dùng lưu trong MongoDB profiles. Nó chưa đồng bộ vector vào `users.preference_vector` hoặc lịch sử vào bảng PostgreSQL `user_interactions`.

### 3.1. `recommendation_profiles`

Mỗi tài khoản có một document; index unique trên `user_id`.

| Trường trong MongoDB | Ý nghĩa |
| --- | --- |
| `_id` | ID document do MongoDB tạo; khác ID tài khoản |
| `user_id` | Khóa tài khoản đã xác thực, dạng `postgres:<users.id>` |
| `preferences.needs` | Nhu cầu người dùng nhập bằng chữ |
| `preferences.max_price` | Ngân sách tối đa, đơn vị VND |
| `preferences.district` | Quận/huyện cần khớp dữ liệu; `null` là không giới hạn quận |
| `initial_vector` | Vector E5 384 chiều của nhu cầu ban đầu; giữ nguyên khi học hành vi |
| `preference_vector` | Vector hiện dùng tìm phòng, kết hợp nhu cầu ban đầu với hành vi |
| `embedding_model` | Tên model tạo vector: `intfloat/multilingual-e5-small`; không chứa trọng số model |
| `profile_generation` | UUID mới khi lưu/sửa nhu cầu, phân biệt lịch sử của nhu cầu cũ và mới |
| `profile_version` | Phiên bản tăng khi hồ sơ thay đổi; dùng kiểm soát cập nhật đồng thời |
| `behavior_since` | Mốc bắt đầu lấy hành vi cho nhu cầu hiện tại |
| `behavior_listing_count` | Số phòng khác nhau có tín hiệu và vector hợp lệ đang tham gia học |
| `behavior_weight` | Tổng trọng số của các phòng đang tham gia học |
| `behavior_blend` | Hệ số trộn hành vi vào vector, từ 0 đến 0,35 |
| `behavior_signal_weights` | Map nội bộ từ ID phòng sang trọng số mạnh nhất, ví dụ `{"1310": 5.0}` |
| `created_at` | Thời điểm tạo hồ sơ lần đầu, UTC |
| `updated_at` | Thời điểm hồ sơ thay đổi gần nhất, UTC |

`GET /recommend/preferences` trả nhu cầu, tên model, thời điểm cập nhật, phiên bản và ba trường `behavior_listing_count`, `behavior_weight`, `behavior_blend`. Vector, generation và map trọng số được giữ nội bộ.

### 3.2. `recommendation_interactions`

Mỗi hành động được nhận tạo một document lịch sử.

| Trường trong MongoDB | Ý nghĩa |
| --- | --- |
| `_id` | ID document sự kiện do MongoDB tạo |
| `user_id` | Tài khoản thực hiện hành động, lấy từ JWT và tra cứu tài khoản |
| `listing_id` | ID phòng trong PostgreSQL; API kiểm tra tồn tại trước khi ghi |
| `type` | `view`, `save`, `contact` hoặc `not_interested` |
| `duration_ms` | Thời gian xem theo milliseconds; có thể `null` |
| `received_at` | Thời điểm server nhận hành động, UTC |
| `profile_generation` | Thế hệ nhu cầu khi ghi hành động; có thể `null` nếu chưa có hồ sơ hoặc hồ sơ cũ thiếu generation |

API trả `event_id` là `_id` chuyển thành chuỗi. Các trường `profile_updated`, `learning_status`, `event_learning_reason`, `profile_version`, `behavior_listing_count`, `learning_warning` trong phản hồi tương tác được tính khi xử lý; chúng không được lưu trong document sự kiện.

Index interactions gồm `user_id ASC, received_at DESC` và `user_id ASC, listing_id ASC, type ASC`. Cả hai collection có index `_id` mặc định.

Cửa sổ học 30 ngày chỉ giới hạn dữ liệu dùng để tính vector. Không có TTL index, nên document cũ không tự bị xóa theo quy tắc này.

### 3.3. Metadata là gì?

Metadata là thông tin mô tả cách tạo, cập nhật và sử dụng hồ sơ. Hai collection hiện tại không có trường riêng tên `metadata`.

- **Nhu cầu:** nhóm `preferences`.
- **Vector để tính độ phù hợp:** `initial_vector`, `preference_vector`.
- **Metadata hồ sơ:** `embedding_model`, `profile_generation`, `profile_version`, `behavior_since`, `created_at`, `updated_at`.
- **Metadata học hành vi:** `behavior_listing_count`, `behavior_weight`, `behavior_blend`, `behavior_signal_weights`.
- **Metadata sự kiện:** `received_at`, `profile_generation`; các trường còn lại định danh tài khoản/phòng và mô tả hành động.

Ví dụ hồ sơ đã kiểm tra có 1 phòng, trọng số 5, hệ số trộn 0,25: một phòng đang đóng góp tín hiệu liên hệ; vector được trộn 25% từ hành vi trước bước chuẩn hóa. 0,25 không phải xác suất người dùng thích phòng.

### 3.4. Quy tắc học hành vi

| Hành động | Trọng số | Điều kiện |
| --- | ---: | --- |
| `view` | 1 | Có `duration_ms >= 5000` |
| `save` | 3 | Phòng có vector hợp lệ, đúng model và active |
| `contact` | 5 | Phòng có vector hợp lệ, đúng model và active |
| `not_interested` | 0 | Loại phòng khỏi gợi ý và tập học |

Một phòng lấy hành động mạnh nhất: xem rồi lưu rồi liên hệ chỉ tính 5. Gửi lặp vẫn ghi lịch sử, không nhân trọng số.

Lấy tối đa 200 phòng khác nhau trong 30 ngày gần nhất, từ lần lưu nhu cầu hiện tại và thuộc cùng generation. Chỉ dùng vector phòng hợp lệ.

```text
W = tổng trọng số của các phòng hợp lệ
alpha = min(0.35, W / 20)
preference_vector = normalize(
    (1 - alpha) * normalize(initial_vector) + alpha * behavior_vector
)
```

`behavior_vector` là trung bình vector phòng có trọng số, sau chuẩn hóa; được tính tạm, không lưu thành trường riêng. Nếu các vector triệt tiêu nhau, giữ vector nhu cầu ban đầu.

Mỗi PUT nhu cầu tạo generation mới, reset vector và metadata hành vi. Lịch sử cũ vẫn còn; hành vi dương generation cũ không ảnh hưởng nhu cầu mới. `not_interested` tiếp tục loại phòng theo lịch sử tài khoản, kể cả sau khi đổi nhu cầu. API hiện chưa có hoàn tác “không quan tâm”.

Cách học này điều chỉnh vector theo quy tắc; chưa huấn luyện lại E5/BGE trên lịch sử người dùng.

## 4. Cài đặt sau khi nhận nhánh

### 4.0. Danh sách cần migrate và dữ liệu cần nhận

Phần thiết kế dữ liệu của chức năng gợi ý được bàn giao bằng các file sau:

| Thành phần | Thay đổi của chức năng này | File/thao tác trên máy nhận |
| --- | --- | --- |
| PostgreSQL `aggregated_listings` | Bổ sung `embedding_model`, `embedded_content_hash`, `embedded_at` nếu thiếu | Chạy [93_recommendation_embeddings.sql](../../infra/db/migrations/93_recommendation_embeddings.sql) trên đúng database đích |
| PostgreSQL `aggregated_listings.embedding_vector` | Cột `VECTOR(384)` đã có trong schema gốc; dữ liệu vector được tạo ở bước embedding | Nhận dữ liệu phòng có vector hoặc tạo vector nếu chưa có |
| PostgreSQL tài khoản | Module dùng auth hiện tại; không thêm cột tài khoản ở migration 93 | Giữ schema auth của nhóm và cấu hình JWT tương ứng |
| MongoDB `recommendation_profiles` | Hồ sơ nhu cầu/vector, index unique `user_id` | Chạy [setup_recommendation_mongo.py](../../scripts/setup_recommendation_mongo.py) vào MongoDB đích |
| MongoDB `recommendation_interactions` | Lịch sử hành vi và hai index truy vấn | Cùng script setup ở trên |

**Thứ tự cho người tổng hợp nhánh:**

1. Merge các file đã commit. Xác định PostgreSQL và MongoDB nào sẽ chạy cho nhóm.
2. Trên PostgreSQL đã có schema dự án, mở Query Tool/SQL editor của đúng database và chạy nội dung file `93_recommendation_embeddings.sql`. File dùng `ADD COLUMN IF NOT EXISTS`; nếu migration 90 đã thêm đủ ba cột thì bước này không thêm lại chúng. Với database trắng, cần dựng schema nền của dự án trước. Không chạy lại các file tạo bảng `20_listings.sql`/`30_users.sql` trên database đã có bảng chỉ để thêm metadata.
3. Nhận/import dữ liệu phòng cùng vector, hoặc dùng database chung đã có vector. Migration tạo cột; dữ liệu vector phải được bàn giao riêng.
4. Khởi tạo MongoDB bằng script dưới đây, đặt URI/tên database của API khớp với setup. Script tạo collection/index, không chèn tài khoản hoặc hồ sơ mẫu. Khi người dùng lưu nhu cầu và tương tác, API tự tạo các trường document theo thiết kế ở mục 3.
5. Cài runtime/model, chạy API và đối chiếu preferences → for-you → listing detail theo checklist mục 6.

Ví dụ MongoDB local, database dùng cho nhóm:

```powershell
./apps/api/.venv/Scripts/python.exe scripts/setup_recommendation_mongo.py --uri mongodb://127.0.0.1:27018/ --database nckh_recommendation
```

MongoDB ở môi trường này không có file ALTER TABLE. Script setup đảm nhiệm collection/index; cấu trúc document do `ProfileRepository` và schema API quản lý. Nếu muốn giữ lịch sử demo, cần chuyển document riêng và kiểm tra ánh xạ ID như mục 2. Chức năng vẫn chạy khi bắt đầu với hai collection rỗng.

**Có phải embed lại không?**

| Dữ liệu máy nhận có | Cần embed lại? |
| --- | --- |
| Cùng kết nối database hiện tại đã có vector | Không, nếu nội dung phòng và model giữ nguyên |
| Restore/import bản dữ liệu đã có vector E5 384 chiều và metadata tương ứng | Không, nếu nội dung phòng và model giữ nguyên |
| Chỉ merge source/migration hoặc nhận dataset gốc chưa có vector | Có, cần tạo vector cho các phòng chưa được embed |
| Có phòng mới, nội dung phòng đổi hoặc đổi model/cách tạo văn bản embedding | Cần tạo lại vector cho dữ liệu bị ảnh hưởng |

Để dùng lại kết quả đã embed, bản bàn giao PostgreSQL phải giữ `id`, nội dung phòng và các cột `embedding_vector`, `embedding_model`, `embedded_content_hash`, `embedded_at`. Nên nhận bản export/backup cập nhật sau lần embedding; dataset gốc trước khi chạy embedding có thể chưa chứa các giá trị này. Nếu database nhận đang có dữ liệu riêng của nhóm, người phụ trách dữ liệu cần kiểm tra ID và nhập phần cần dùng, tránh ghi đè database đó bằng bản demo.

Sau khi có các cột, chạy SQL chỉ đọc để kiểm tra dữ liệu nhận được:

```sql
SELECT
    COUNT(*) AS total_rooms,
    COUNT(embedding_vector) AS rooms_with_vector,
    COUNT(*) FILTER (
        WHERE embedding_vector IS NOT NULL
          AND embedding_model = 'intfloat/multilingual-e5-small'
    ) AS rooms_with_e5_vector
FROM public.aggregated_listings;
```

Bản dữ liệu đã làm việc trước đó có 788/789 phòng có vector. Dùng con số đó để đối chiếu nếu nhận đúng cùng snapshot; database đã thêm/bớt phòng sẽ có số đếm khác. SQL trên kiểm tra sự hiện diện và tên model, chưa xác nhận vector còn khớp nội dung sau khi sửa phòng. Phòng chưa có vector sẽ chưa tham gia gợi ý.

Máy nhận vẫn cần model E5 để embed nhu cầu mới của người dùng, và BGE nếu dùng rerank. Tải model trên máy mới không có nghĩa phải embed lại toàn bộ phòng.

### 4.1. Dùng database handoff như máy hiện tại

Yêu cầu PostgreSQL handoff đã được dựng/import tại `localhost:5454`, database và user `nckh_handoff`. Runner không tự tạo PostgreSQL hoặc import dataset.

Từ thư mục gốc dự án, trong PowerShell:

```powershell
python -m venv apps/api/.venv
./apps/api/.venv/Scripts/python.exe -m pip install -r apps/api/requirements-recommendation.txt
docker compose -f compose.recommendation-mongo.yaml up -d
$env:RECOMMENDATION_MONGO_URI = 'mongodb://127.0.0.1:27018/'
$env:RECOMMENDATION_MONGO_DATABASE = 'nckh_recommendation_dev'
./apps/api/.venv/Scripts/python.exe scripts/setup_recommendation_mongo.py --database nckh_recommendation_dev
./apps/api/.venv/Scripts/python.exe scripts/run_recommendation_api.py --full-api
```

Bỏ bước tạo/cài môi trường nếu đã có môi trường phù hợp. Máy đã kiểm tra dùng Python 3.11.

Lệnh cuối hỏi mật khẩu PostgreSQL, chạy API chung tại `http://127.0.0.1:8000/docs`, dùng cùng database cho auth/listings/recommendation và tắt scheduler crawl. Đổi cổng bằng `--port 8002`. Runner không tự reload; khởi động lại sau khi sửa code.

`--with-auth` chạy API gợi ý riêng ở cổng 8001; `--full-api` có cả auth/listings/recommendation. Lấy token từ chính API đang dùng. Runner có thể sinh JWT secret cho lần chạy local; đăng nhập lại sau khi khởi động lại.

### 4.2. Dùng database chung của nhóm

Cài requirements recommendation trong runtime API. Cấu hình `DATABASE_URL` tới PostgreSQL của nhóm và đặt các biến trong cấu hình riêng của môi trường:

```dotenv
RECOMMENDATION_AUTH_SOURCE=postgres
RECOMMENDATION_MONGO_URI=mongodb://127.0.0.1:27018/
RECOMMENDATION_MONGO_DATABASE=nckh_recommendation
RECOMMENDATION_DATABASE_URL=
```

URI trên dành cho API chạy trực tiếp trên Windows với compose Mongo đi kèm. Dùng URI dịch vụ thực tế ở môi trường khác.

Giữ `RECOMMENDATION_DATABASE_URL` trống để recommendation và `/listings` đọc cùng catalog. Tên database phải khớp giữa setup và API:

```powershell
./apps/api/.venv/Scripts/python.exe scripts/setup_recommendation_mongo.py --database nckh_recommendation
```

Setup mặc định URI local và database `nckh_recommendation_dev`; truyền `--uri`/`--database` khi dùng nơi khác. API thông thường mặc định database `nckh` nếu chưa cấu hình, nên đặt rõ tên database.

Chạy `app.main` bằng quy trình của nhóm. Trên Windows, đặt `DATABASE_URL`/`REDIS_URL` dùng địa chỉ host truy cập được. Runner `run_recommendation_api.py` cố định database handoff, không tự chuyển sang database chung.

Nếu chạy API trực tiếp trên Windows, sau khi đặt cấu hình riêng, có thể dùng:

```powershell
./apps/api/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

PostgreSQL đích cần:

- Schema auth/listings của API chung, extension PostGIS và pgvector.
- `aggregated_listings` có phòng và `embedding_vector VECTOR(384)`.
- Các trường `embedding_model`, `embedded_content_hash`, `embedded_at`.
- Vector tạo bằng `intfloat/multilingual-e5-small` và tên model được ghi đúng.

Migration `infra/db/migrations/93_recommendation_embeddings.sql` thêm ba trường metadata; không tạo phòng/vector. Áp dụng nếu database đích thiếu cột. API không tự chạy migration hoặc backfill embedding.

Catalog handoff dùng `scripts/embed_handoff_listings.py`: `--apply-migration`, rồi `--limit 5` hoặc `--all`. Script cần view `catalog_handoff_v1` và chỉ dùng database handoff. Database chung có `scripts/index_listing_embeddings.py` cho phòng active đã cleaned; thống nhất tập phòng và cách tạo vector với người phụ trách dữ liệu.

Với `index_listing_embeddings.py`, truyền `--database-url` của database đích khi không dùng database local từ compose. Script này không tự dùng biến `DATABASE_URL`; mặc định nó lấy cổng từ compose và tài khoản/database từ `POSTGRES_*`. Kiểm tra đúng database trước khi tạo vector.

Model tải khi dùng lần đầu và cache trên máy chạy. Máy mới cần E5; BGE chỉ cần khi dùng rerank. Cache model không đi theo Git.

### 4.3. Nếu API chạy bằng Docker

Dockerfile API hiện chỉ cài `requirements.txt`; compose chính chưa truyền biến recommendation. Người phụ trách triển khai cần:

- Cài `requirements-recommendation.txt` và các requirements được tham chiếu trong image.
- Truyền biến recommendation vào service API.
- Đặt URI Mongo truy cập được từ container; dùng hostname service trên mạng chung hoặc địa chỉ host phù hợp.
- Chuẩn bị catalog/vector PostgreSQL và model/cache cho runtime đó.

`localhost:27018` bên trong container API trỏ vào container API. Hai compose hiện chưa tự có mạng dịch vụ chung. Kết quả chạy local chưa xác nhận image Docker của nhóm.

## 5. Frontend cần làm gì?

Base URL local: `http://127.0.0.1:8000`. Trừ preview, các route recommendation cần `Authorization: Bearer <access_token>`. Backend tự xác định tài khoản; frontend không gửi `user_id`.

| Method | Path | Mục đích |
| --- | --- | --- |
| POST | `/recommend/preview` | Thử nhu cầu chưa đăng nhập, không lưu |
| PUT | `/recommend/preferences` | Lưu/sửa nhu cầu |
| GET | `/recommend/preferences` | Đọc nhu cầu và metadata |
| GET | `/recommend/for-you?top_k=10&rerank=false` | Lấy danh sách “Dành cho bạn” |
| POST | `/recommend/interactions` | Ghi hành vi và thử cập nhật hồ sơ |
| GET | `/listings/{listing_id}` | Mở chi tiết phòng |

### 5.1. Form nhu cầu

Body PUT:

```json
{
  "needs": "Phòng có máy lạnh, nhà vệ sinh riêng, gần Đại học Cần Thơ",
  "max_price": 3000000,
  "district": null
}
```

`needs` từ 1–1.500 ký tự và phải nằm trong giới hạn token E5. `max_price` là số nguyên dương, tối đa 100.000.000 VND. `district` khớp tên dữ liệu hoặc null.

Đọc nhu cầu trước khi hiện form. PUT chỉ khi người dùng lưu/sửa; không PUT lại mỗi lần mở trang vì thao tác đó reset học hành vi.

### 5.2. Danh sách gợi ý và mở chi tiết

Response chứa `items`:

| Trường | Frontend dùng |
| --- | --- |
| `listing_id` | Khóa thẻ và ID mở chi tiết |
| `title`, `price`, `area`, `district` | Hiển thị tên, giá, diện tích, khu vực; area/district có thể null |
| `housing_type`, `offer_kind` | Nhãn nếu có; có thể null |
| `description_is_partial` | Mô tả nguồn bị thiếu nếu xác định được; có thể null |
| `source_url`, `source_contact_url` | Link nguồn/liên hệ nếu có; có thể null |
| `cosine_score`, `cosine_rank` | Điểm/hạng để kiểm tra; không phải phần trăm phù hợp |
| `rerank_score` | Điểm BGE khi rerank; có thể null |

Response còn có `preferences`, `eligible_count`, `retrieved_count`, `embedding_model`, `reranker_model`, `elapsed_ms`, `warnings`. `eligible_count` là tổng phòng qua lọc; `retrieved_count` là số ứng viên đã lấy, có thể lớn hơn số item khi rerank. `top_k` từ 1 đến 20.

ID trong gợi ý tên là `listing_id`; ID trong response chi tiết tên là `id`. Bấm thẻ gọi detail bằng đúng listing_id, đối chiếu ID/tên/giá.

Item gợi ý chưa trả ảnh. Nếu Figma cần ảnh thẻ, thống nhất cách lấy từ chi tiết/cache hoặc bổ sung trường API; tránh gọi detail liên tục mỗi lần render.

### 5.3. Gửi hành vi thật

Body POST khi lưu phòng:

```json
{
  "listing_id": 1310,
  "type": "save",
  "duration_ms": null
}
```

ID trên là ví dụ; lấy ID từ response thực tế.

- `view`: đo thời gian người dùng thực sự xem, gửi milliseconds khi kết thúc lượt xem; không gửi theo từng giây/mỗi lần render.
- `save`: gửi sau thao tác lưu/yêu thích.
- `contact`: gửi sau khi bấm gọi/nhắn/mở liên hệ; chưa chứng minh chủ trọ đã trả lời.
- `not_interested`: gửi khi người dùng chọn không quan tâm, rồi bỏ thẻ/tải lại gợi ý.

`save` ở module này ghi tín hiệu gợi ý; chưa cung cấp API danh sách yêu thích hoặc bỏ lưu. Nếu giao diện quản lý yêu thích, cần nối chức năng lưu riêng.

Hành vi được dùng ở lần lấy gợi ý tiếp theo. Giao diện phải tải lại dữ liệu để thấy thay đổi.

Phản hồi 201 nghĩa là đã ghi sự kiện, không đảm bảo vector vừa đổi:

| Trạng thái phản hồi | Ý nghĩa |
| --- | --- |
| `learning_status=updated` | Hồ sơ đã thay đổi trong lượt xử lý |
| `learning_status=unchanged` | Hồ sơ không cần đổi |
| `learning_status=no_profile` | Chưa lưu nhu cầu |
| `learning_status=pending` | Sự kiện đã lưu; lần đọc tiếp theo thử cập nhật lại |
| `profile_updated` | Hồ sơ có được cập nhật trong lượt này không |
| `event_learning_reason` | Lý do riêng của sự kiện vừa gửi |
| `learning_warning` | Mô tả lỗi khi cập nhật/giải thích |

Reason gồm `eligible`, `duplicate_signal`, `short_view`, `excluded`, `unavailable_embedding`, `stale_generation`, `no_profile`, `pending`. `duplicate_signal` là phòng đã có tín hiệu bằng/mạnh hơn; `short_view` là chưa đủ 5 giây. `profile_updated=true` còn có thể do phục hồi lịch sử cũ; đọc thêm reason để biết sự kiện mới có đóng góp hay không. Giải thích đầy đủ: [Recommendation_Behavior.md](Recommendation_Behavior.md).

`event_learning_reason=pending` có thể xuất hiện khi hồ sơ đã cập nhật nhưng lượt đọc dùng để giải thích sự kiện bị lỗi. Phân biệt với `learning_status=pending`, là trạng thái chưa cập nhật được hồ sơ; đọc thêm `profile_updated` và `learning_warning`.

### 5.4. Xác thực và trạng thái trang

1. Chưa đăng nhập: yêu cầu đăng nhập hoặc dùng preview.
2. Đã đăng nhập: đọc preferences; nếu 404 thì hiện form.
3. Lưu nhu cầu thành công: gọi for-you và hiện items.
4. Bấm thẻ: mở chi tiết bằng listing_id.
5. Gửi tương tác theo hành động thật.
6. Lần tải gợi ý tiếp theo dùng hồ sơ đã cập nhật.

Next.js hiện dùng cookie HttpOnly trong `apps/web/src/lib/session.ts`. Client JavaScript không đọc access token từ cookie này. Thêm Route Handler recommendation theo cách auth/listings hiện có: server đọc cookie, gọi FastAPI với bearer token; client gọi route nội bộ Next.js. Dùng `API_INTERNAL_URL`/`NEXT_PUBLIC_API_URL` theo cấu hình hiện tại.

Khi token hết hạn, refresh trong Route Handler/Server Action rồi thử lại một lần. Nếu đổi sang gọi FastAPI trực tiếp từ trình duyệt, cần cấu hình CORS và cách cấp token; API hiện chưa có CORS cho luồng đó.

| Tình huống | Xử lý |
| --- | --- |
| 401/token hết hạn; thiếu token có thể nhận 403 từ auth hiện tại | Refresh hoặc yêu cầu đăng nhập |
| 404 chưa có nhu cầu | Hiện form |
| 404 phòng không tồn tại | Thông báo và tải lại danh sách |
| 409 hồ sơ/model thay đổi | Đọc detail, tải lại hoặc lưu lại nhu cầu theo nguyên nhân |
| 422 input không hợp lệ | Hiện lỗi nhập |
| 503 database/model/xác thực chưa cấu hình | Hiện lỗi dịch vụ; kiểm tra cấu hình |
| 200 với items rỗng | Hiện trạng thái không có phòng phù hợp |

## 6. Checklist khi tổng hợp nhánh

- [ ] Đã nhận source, requirements, migration, scripts, compose và tài liệu qua commit.
- [ ] Xử lý conflict ở `app/main.py`: giữ router/init/lifecycle recommendation và các module khác.
- [ ] Giữ các trường recommendation trong `app/config.py`.
- [ ] API dùng đúng database tài khoản/phòng của môi trường nhận.
- [ ] Cài dependencies, chuẩn bị E5 và BGE nếu cần.
- [ ] Mongo URI/database khớp; tạo index bằng setup hoặc lần dùng API đầu tiên.
- [ ] Catalog có vector E5 384 chiều và metadata model.
- [ ] Tài khoản mới lưu được nhu cầu; hai tài khoản đọc hồ sơ riêng.
- [ ] For-you trả phòng thật; detail khớp ID/tên/giá.
- [ ] Hành vi cập nhật metadata; gửi lặp không nhân trọng số.
- [ ] Phòng not_interested không xuất hiện lại.
- [ ] Frontend dùng đúng auth, ID, VND và milliseconds.
- [ ] Nếu Docker: bổ sung dependencies, biến môi trường và kết nối Mongo cho container.

Nếu tìm kiếm `/listings` rỗng nhưng gợi ý có phòng, đối chiếu cleaning: tìm kiếm hiện lấy tin user hoặc tin cleaned/phong_tro; gợi ý lấy tin active có embedding. Thống nhất với người phụ trách dữ liệu trước khi triển khai.

## 7. Việc còn lại và bản đồ code

Rerank đã chạy nhưng từng ghi nhận khoảng 42,8–129 giây trên CPU. Dùng `rerank=false` khi nối giao diện ban đầu; đánh giá trước khi bật mặc định. Rerank lấy 50 ứng viên theo vector cá nhân hóa rồi xếp lại bằng nhu cầu dạng chữ; chưa trộn điểm hành vi riêng vào bước BGE.

`rerank` là tham số của request API. Khi frontend luôn gọi `rerank=true`, backend tự chạy BGE cho mỗi lần lấy gợi ý; người dùng không cần một nút bật/tắt. Hiện API mặc định `false`, nên request bỏ tham số này chỉ xếp theo cosine. Có thể đổi mặc định hoặc cấu hình lời gọi frontend khi nhóm chốt tốc độ và chất lượng.

Cần tập nhu cầu/phòng có nhãn để đánh giá Precision@10/NDCG@10. “Gần Đại học Cần Thơ” hiện là ý trong văn bản truy vấn, chưa có bộ lọc khoảng cách ở module này. Điểm cao chưa chứng minh gần trường/còn phòng; giá và tình trạng nguồn cần xác minh.

| File trong `apps/api/app/room_service/recommendation/` | Trách nhiệm |
| --- | --- |
| `router.py` | Routes, khởi tạo và nối auth |
| `schemas.py` | Request/response và validation |
| `service.py` | Luồng gợi ý, nhu cầu, cập nhật hồ sơ |
| `repo.py` | PostgreSQL và MongoDB |
| `models.py` | Tải/chạy E5, BGE |
| `behavior.py` | Trọng số, chuẩn hóa, trộn vector |
| `auth.py` | Tài khoản JWT thành user_id |

Kiểm thử nằm ở `apps/api/tests/test_recommendation_behavior.py` và `test_recommendation_mongo.py`. Đã chạy lại cả hai bộ khi chuẩn bị commit nhánh bàn giao ngày 07/10/2026: 58 kiểm thử đạt, gồm các kiểm thử MongoDB thật trong database tạm riêng. Lệnh kiểm thử và chi tiết thuật toán: [Recommendation_Behavior.md](Recommendation_Behavior.md). Người nhận cần kiểm tra lại cấu hình và dữ liệu trên môi trường sau merge.

### Nhận nhánh bàn giao

Người tổng hợp nhận nhánh `codex/goi-y-phong-tro` trên GitHub và đọc mục 4.0 để áp dụng thay đổi dữ liệu. Nhánh kế thừa code từ `feature/update-local`; khi so sánh riêng phần gợi ý, dùng nhánh đó làm mốc. Sau khi tổng hợp các nhánh, kiểm tra theo mục 6.

Source và tài liệu đi theo Git; bản backup PostgreSQL chứa vector và dữ liệu MongoDB được bàn giao riêng nếu nhóm cần dùng lại. Không đưa .env, token, mật khẩu, model cache, archive database hoặc môi trường Python vào commit.
