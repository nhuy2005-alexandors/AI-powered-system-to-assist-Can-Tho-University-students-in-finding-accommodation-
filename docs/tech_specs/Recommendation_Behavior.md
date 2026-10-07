# Cá nhân hóa gợi ý bằng hành vi

## Luồng hiện tại

1. `PUT /recommend/preferences`: E5 tạo vector nhu cầu ban đầu; MongoDB lưu hồ sơ với một thế hệ mới.
2. `POST /recommend/interactions`: ghi hành động theo tài khoản JWT, rồi cập nhật hồ sơ từ lịch sử tương tác.
3. `GET /recommend/preferences` và `GET /recommend/for-you`: tính lại hồ sơ nếu có sự kiện chưa áp dụng hoặc đã hết cửa sổ lịch sử.
4. `/recommend/for-you` dùng `preference_vector` mới cho cosine. Giới hạn giá, quận và loại bỏ tin không quan tâm vẫn được áp dụng.

Đây là phương pháp content-based dùng implicit feedback, với trọng số khởi tạo theo quy tắc. Chưa huấn luyện mô hình trên lịch sử người dùng.

## Cách tính

| Hành động | Trọng số | Điều kiện |
|---|---:|---|
| `view` | 1 | `duration_ms >= 5000` |
| `save` | 3 | Phòng có vector hợp lệ và đúng model |
| `contact` | 5 | Phòng có vector hợp lệ và đúng model |
| `not_interested` | 0 | Loại tin khỏi gợi ý và khỏi tập học |

Lịch sử lấy trong 30 ngày gần nhất, tối đa 200 phòng khác nhau, kể từ lần lưu nhu cầu mới nhất. Một phòng chỉ đóng góp hành động có trọng số cao nhất: xem + lưu + liên hệ cùng một phòng chỉ tính 5. Gửi lặp hành động vẫn được ghi lịch sử nhưng không nhân trọng số. Chỉ dùng vector 384 chiều hữu hạn, khác vector 0, của phòng còn active và cùng embedding model.

`behavior_vector` là vector trung bình có trọng số của các phòng hợp lệ, sau chuẩn hóa. Với tổng trọng số `W`:

```text
alpha = min(0.35, W / 20)
preference_vector = normalize((1-alpha)*normalize(initial_vector) + alpha*behavior_vector)
```

Vector luôn được tính lại từ `initial_vector`; không cộng tiếp vào vector đã học. Vector gốc được giữ nguyên. Nếu trung bình các vector triệt tiêu nhau, hệ thống dùng lại vector nhu cầu ban đầu. Các trọng số và mức 35% cần được đánh giá trên dữ liệu thực tế.

## Đồng thời, đổi nhu cầu và phục hồi

- Mỗi lần lưu nhu cầu tạo `profile_generation` mới, đặt lại trạng thái hành vi và tăng `profile_version`.
- Sự kiện được gắn với thế hệ nhu cầu đang dùng khi ghi. Sự kiện của thế hệ cũ vẫn có trong lịch sử nhưng không ảnh hưởng nhu cầu mới.
- Cập nhật MongoDB dùng điều kiện thế hệ + phiên bản; xung đột sẽ đọc và tính lại tối đa ba lần. Lượt cập nhật cũ không ghi đè nhu cầu mới.
- Hồ sơ cũ chưa có thế hệ vẫn đọc được lịch sử cũ. Lần tính lại đầu tiên bổ sung metadata học hành vi.
- Ghi sự kiện và cập nhật hồ sơ là hai thao tác. Nếu ghi được nhưng cập nhật thất bại, API trả `learning_status: pending`. Lần đọc hồ sơ/gợi ý tiếp theo thử áp dụng lại lịch sử.
- Quy tắc `not_interested` tiếp tục loại tin theo toàn bộ lịch sử tài khoản, kể cả sau khi đổi nhu cầu.

## Kiểm tra bằng Swagger

Script local chạy không có tự reload. Sau khi sửa code, dừng API bằng Ctrl+C rồi chạy lại từ thư mục dự án:

```powershell
.\apps\api\.venv\Scripts\python.exe scripts/run_recommendation_api.py --with-auth
```

1. Mở `http://127.0.0.1:8001/docs`, đăng nhập lại và Authorize bằng access token mới.
2. Gọi `GET /recommend/preferences`: ghi lại `profile_version`, `behavior_listing_count`, `behavior_weight`, `behavior_blend`.
3. Gọi `GET /recommend/for-you?top_k=10&rerank=false`: ghi lại thứ tự và điểm cosine.
4. Gửi một hành động với ID có trong danh sách, ví dụ:

```json
{
  "listing_id": 1310,
  "type": "save",
  "duration_ms": null
}
```

5. Phản hồi vẫn là 201 khi sự kiện được lưu. `profile_updated` cho biết toàn bộ hồ sơ có được cập nhật trong lượt này; `learning_status` cho biết trạng thái cập nhật. `event_learning_reason` giải thích riêng hành động vừa gửi:

| Giá trị | Ý nghĩa |
|---|---|
| `eligible` | Hành động có thể đóng góp vào hồ sơ |
| `duplicate_signal` | Phòng đã có tín hiệu bằng hoặc mạnh hơn |
| `short_view` | Chưa đủ thời gian xem hoặc chưa gửi thời gian |
| `excluded` | Tin được đánh dấu không quan tâm |
| `unavailable_embedding` | Tin không có vector tương thích/hợp lệ trong tập học hiện tại |
| `stale_generation` | Nhu cầu đã đổi trong lúc ghi sự kiện |
| `no_profile` | Chưa lưu nhu cầu |
| `pending` | Sự kiện đã ghi; chưa cập nhật được hồ sơ hoặc chưa đọc đủ dữ liệu để giải thích sự kiện |

`profile_updated: true` có thể do phục hồi lịch sử trước đó hoặc bổ sung metadata hồ sơ cũ; kiểm tra thêm `event_learning_reason` để biết hành động mới có hợp lệ. Mức ảnh hưởng là heuristic, không phải xác suất người dùng thích phòng.

`event_learning_reason: pending` còn có thể đi cùng `learning_status: updated` khi hồ sơ đã cập nhật nhưng lượt đọc giải thích sự kiện gặp lỗi. `learning_status: pending` mới cho biết phần cập nhật hồ sơ đang chờ thử lại. Xem `learning_warning` để biết nguyên nhân.

6. Gọi lại preferences và for-you. Hồ sơ phải giữ ngân sách/quận đã nhập; điểm cosine phản ánh vector mới. Thứ tự top 10 có thể giữ nguyên nếu các phòng quá giống nhau; metadata và vector trong kiểm thử xác nhận cập nhật.
7. Gửi lặp cùng hành động: trọng số và vector không bị nhân lên. Gửi `contact` cho phòng mới chỉ có `save`: trọng số của phòng tăng từ 3 lên 5. Gửi `not_interested`: phòng biến mất khỏi gợi ý và tập học.

## Rerank

`rerank=true` lấy 50 ứng viên theo vector đã cá nhân hóa, sau đó BGE xếp lại dựa trên nhu cầu dạng chữ và quận. Hành vi tác động tập ứng viên; điểm BGE chưa trộn thêm điểm hành vi. Response có thông báo phạm vi này khi hồ sơ đã có ảnh hưởng hành vi. Kiểm tra thay đổi theo hành vi với `rerank=false` trước.

Việc xác nhận rerank chạy không thay thế đánh giá chất lượng hoặc tốc độ. Lần thử trước trong cuộc hội thoại mất khoảng 42.8 giây và vẫn đưa tin nhắc các trường khác lên cao. Giao diện Dành cho bạn và các sự kiện trên website là bước tích hợp tiếp theo.

## Kiểm thử

Offline, không tải model:

```powershell
.\apps\api\.venv\Scripts\python.exe -m pytest apps/api/tests/test_recommendation_behavior.py -q
```

Với MongoDB local đang chạy, kiểm thử kho dữ liệu thật dùng database tạm riêng; không sửa hồ sơ người dùng:

```powershell
$env:RECOMMENDATION_TEST_MONGO_URI = 'mongodb://127.0.0.1:27018/'
.\apps\api\.venv\Scripts\python.exe -m pytest apps/api/tests/test_recommendation_mongo.py -q
```
