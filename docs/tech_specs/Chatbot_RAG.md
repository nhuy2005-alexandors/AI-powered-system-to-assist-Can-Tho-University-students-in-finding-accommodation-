# Chatbot RAG tìm nhà trọ

## Phạm vi đã triển khai

- `POST /chat/ask`: guest hoặc user đăng nhập, tối đa 5 listing và nguồn.
- Chat stateless: không có route history/feedback và không lưu nội dung hội thoại.
- Parse tiếng Việt: giá, diện tích, quận/huyện, tiện ích, giới tính, khoảng cách/thời gian và loại tin.
- PostgreSQL dùng chung `aggregated_listings` với trang tìm trọ/bản đồ; Redis vẫn là dependency/cache chung.
- Exact cosine pgvector + SQL filter + quality/freshness/risk ranking.
- `multilingual-e5-small` là provider tùy chọn; thiếu model thì API trả `degraded=true` và dùng lexical/structured retrieval.
- Generator mặc định: Qwen `qwen2.5:7b` qua Ollama local; Gemini là fallback tùy chọn khi có `GEMINI_API_KEY`; cuối chuỗi là template grounded.
- Chi tiết cấu hình và vận hành: `docs/AI_CHAT_RISK_INTEGRATION.md`.

## Áp migration và seed mà không xóa volume

Không chạy `infra/db/reset_and_seed.*` vì các script cũ đó xóa volume.

```powershell
docker compose up -d db --build
python scripts/generate_fake_listings.py --seed 2026
python scripts/apply_chatbot_dev.py
```

Script Python đọc host port PostgreSQL từ `docker-compose.yml`; không mặc định cứng 5432/5433. Nếu host port đang bị ứng dụng khác giữ, có thể áp từ trong container:

```powershell
docker cp infra/db/migrations/90_chatbot.sql nckh-db-1:/tmp/90_chatbot.sql
docker exec nckh-db-1 psql -U nckh -d nckh -v ON_ERROR_STOP=1 -f /tmp/90_chatbot.sql
docker cp infra/db/seeds/dev_chatbot.sql nckh-db-1:/tmp/dev_chatbot.sql
docker exec nckh-db-1 psql -U nckh -d nckh -v ON_ERROR_STOP=1 -f /tmp/dev_chatbot.sql
```

Seed chỉ sở hữu namespace `source='dev_seed'`, email `dev2026.*` và session metadata `seed=chatbot-2026`. Chạy lặp lại không nhân đôi dữ liệu thuộc namespace này. Không dùng seed trong production.

## Tạo embedding thật

```powershell
python -m pip install -r apps/api/requirements-ml.txt
python scripts/index_listing_embeddings.py --model intfloat/multilingual-e5-small
```

Indexer dùng prefix `passage:`; query provider dùng `query:`. Cả hai chuẩn hóa L2 và bắt buộc đúng 384 chiều. Nếu package/model không tải được, script dừng với thông báo degraded và không ghi vector giả.
Requirements ML ghim PyTorch CPU để tránh tải các wheel CUDA rất lớn trên máy không có GPU.

## Chạy và kiểm thử

```powershell
docker compose up -d --build
docker compose exec api python -m pytest -q
python eval/chatbot_eval.py
cd apps/web
npm install
npm run build
```

Báo cáo evaluation: `eval/reports/chatbot_eval.json` và `eval/reports/chatbot_eval.md`.

## Năm câu hỏi thử nhanh

1. `Tìm phòng trọ dưới 2 triệu ở Ninh Kiều có wifi.`
2. `Phòng có máy lạnh và gác, giá không quá 1,8 triệu.`
3. `Tìm phòng cho nữ cách trường dưới 2 km.`
4. `Có phòng nào cho nuôi thú cưng và giờ giấc tự do không?`
5. `Tìm nhà nguyên căn dưới 4 triệu ở Cái Răng.`

## Giới hạn có chủ đích

- Dataset khoảng 1.000 listing dùng exact cosine; chưa tạo HNSW/IVFFlat trước khi có benchmark production.
- Core image không đóng gói `sentence-transformers` để giữ image nhẹ. Muốn vector semantic phải cài requirements ML và chạy indexer.
- LLM chỉ nhận tối đa 5 listing đã retrieval; confidence threshold và citations vẫn được giữ trước bước sinh câu trả lời.
