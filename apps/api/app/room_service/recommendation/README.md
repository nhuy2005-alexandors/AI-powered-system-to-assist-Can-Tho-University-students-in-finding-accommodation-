# Gợi ý phòng trọ

Module dùng E5 để biểu diễn nhu cầu, cosine để tìm phòng và BGE để rerank khi được bật. Hồ sơ được cập nhật từ lượt xem, lưu và liên hệ. Nhu cầu/lịch sử lưu trong MongoDB; phòng và vector phòng lưu trong PostgreSQL.

## Tài liệu bàn giao

Đọc [Recommendation_Handoff.md](../../../../../docs/tech_specs/Recommendation_Handoff.md) để biết:

- Cài đặt và cấu hình sau khi merge.
- Ý nghĩa từng trường trong hai collection MongoDB.
- Hợp đồng API và các việc frontend cần làm.
- Dữ liệu cần bàn giao riêng với code và các giới hạn còn lại.

Chi tiết trọng số, cập nhật đồng thời và kiểm thử: [Recommendation_Behavior.md](../../../../../docs/tech_specs/Recommendation_Behavior.md).

## Chạy local

Từ thư mục gốc, khi PostgreSQL handoff và môi trường Python đã sẵn sàng:

```powershell
docker compose -f compose.recommendation-mongo.yaml up -d
./apps/api/.venv/Scripts/python.exe scripts/run_recommendation_api.py --full-api
```

Mở `http://127.0.0.1:8000/docs`, đăng nhập và dùng token do API đó cấp. Runner hỏi mật khẩu PostgreSQL handoff, dùng cùng catalog cho auth/listings/recommendation và tắt scheduler crawl.

Mongo local dùng `localhost:27018`, database `nckh_recommendation_dev` khi chưa đặt URI riêng. Ở API chung của nhóm, đặt rõ URI/database và `RECOMMENDATION_AUTH_SOURCE=postgres`; để `RECOMMENDATION_DATABASE_URL` trống khi dùng cùng catalog với listings.

## Luồng

1. PUT `/recommend/preferences`: lưu nhu cầu và vector ban đầu.
2. GET `/recommend/for-you`: tìm phòng bằng vector sở thích hiện tại.
3. POST `/recommend/interactions`: ghi hành vi rồi cập nhật hồ sơ.
4. GET preferences/for-you: thử phục hồi các cập nhật chưa áp dụng.

Mỗi phòng đóng góp hành động hợp lệ mạnh nhất; gửi lặp không nhân trọng số. Sửa nhu cầu đặt lại học hành vi. `not_interested` loại phòng theo lịch sử tài khoản.

Rerank mặc định tắt vì các lần chạy CPU còn chậm. Hành vi ảnh hưởng tập ứng viên; BGE xếp lại theo nhu cầu dạng chữ. Chất lượng và tốc độ cần đánh giá trước khi bật mặc định.
