# Review, Reports và bộ đánh giá từ PHUC

Đích: `feature/ghep-ban-chat` tại `D:\feature-ghep-ban-chat`.
Chuyển chọn lọc mã nguồn; không nhập 789 tin hoặc gộp dữ liệu từ PHUC.

## Đánh giá nhà trọ

- API `GET/POST /listings/{id}/reviews`, mỗi tài khoản một đánh giá 1–5 sao.
- Chủ tin không tự đánh giá; tin hidden/expired không nhận đánh giá mới.
- Bình luận được chuẩn hóa, sàng lọc cảm xúc và lưu phiên bản mô hình.
- `/admin/reviews` cho phép duyệt hoặc ẩn; API kiểm tra quyền admin.
- Bình luận bị gắn cờ vẫn hiển thị cho đến khi admin quyết định ẩn, giống PHUC.
- Sentiment là hỗ trợ sàng lọc. Bộ câu seed nhỏ, còn lỗi câu không dấu/phủ định;
  không dùng xác suất tiêu cực làm xác suất lừa đảo hoặc kết quả nghiên cứu.
- Bảng mới `listing_reviews` giữ độc lập với bảng `reviews`/`place_reviews` cũ;
  không sửa hoặc chuyển nhãn đánh giá Google Maps.

## Báo cáo và quản trị

- `POST /listings/{id}/report`, `GET /reports/mine`.
- Chặn báo cáo pending trùng bằng cả service và unique index trong DB.
- `/admin`, `/admin/reports`, `/admin/listings`, `/admin/users` dùng quyền admin.
- Admin xác nhận/gắn cờ, ẩn hoặc bác báo cáo; lưu người xử lý, thời gian và ghi chú.
- Xử lý một báo cáo sẽ xử lý các báo cáo pending cùng tin, theo luồng PHUC.
- Bác báo cáo giữ nguyên trạng thái tin; không làm sống lại tin đã ẩn/quá hạn.
- Reports đã tách khỏi risk engine PHUC: báo cáo mới chờ xác minh, không tự sửa điểm risk.
- Nút Quản lý mở dashboard; nhập tin vẫn dùng `/quan-ly/nha-tro` của feature.

## Migration

`101_reports_moderation.sql` và `102_reviews_sentiment.sql` có thể chạy lại.
Dockerfile DB đã thêm hai migration trước bước tạo DB test. DB đang có dữ liệu
phải áp thủ công hai file này; rebuild image DB không tự chạy lại init scripts.
Tên mới tránh đụng migration matching/chat/POI của feature.

Lưu ý môi trường hiện tại: compose project `nckh` đang dùng lại DB cũ có 789 tin.
Đây không phải DB riêng 87–89 tin của feature và lần chuyển này không nhập/gộp tin.
Đã sao lưu DB vào `.local-backups/feature-before-baseline-20261012.dump` trước khi
bổ sung schema nền của feature (90–100). Riêng migration 94 chỉ áp DDL, không chạy
đoạn UPDATE hồ sơ mẫu. Không dùng `docker compose down -v` để chuyển bộ dữ liệu.
Nếu cần chạy song song PHUC và feature với hai DB độc lập, cần cấu hình project,
volume và cổng riêng; đổi thư mục mã nguồn không tự tách DB.

```powershell
docker cp infra/db/migrations/101_reports_moderation.sql nckh-db-1:/tmp/101.sql
docker exec nckh-db-1 psql -v ON_ERROR_STOP=1 -U nckh -d nckh -f /tmp/101.sql
docker cp infra/db/migrations/102_reviews_sentiment.sql nckh-db-1:/tmp/102.sql
docker exec nckh-db-1 psql -v ON_ERROR_STOP=1 -U nckh -d nckh -f /tmp/102.sql
```

## Đánh giá thực nghiệm

- `eval/ragas_eval.py`: chuyển khung PHUC sang API thật `/chatbot/ask`, bắt buộc
  token admin để lấy evaluation contexts. Không đụng `/chat` ghép bạn.
- Tách `collect` và `score`, checkpoint từng câu, tiếp tục mẫu lỗi khi chạy lại.
- Lưu hash dataset, code, phiên bản prompt, model sinh/chấm, cấu hình và snapshot
  của corpus pháp lý, tin đăng và graph nếu bật. Phát hiện corpus/model thay đổi
  giữa các lượt hoặc trong một lượt collect.
- Endpoint metadata riêng: `GET /admin/documents/evaluation-manifest`; không trả
  nội dung tài liệu, thông tin cá nhân hay khóa API.
- Báo cáo p50/p95, lỗi, partial/no-answer/degraded và độ phủ của từng metric.
- Kiểm tra trích dẫn dùng hàm của sản phẩm: chỉ đối chiếu số thứ tự nguồn;
  faithfulness chấm việc câu trả lời có được nội dung nguồn hỗ trợ hay không.
- RAGAS dùng Faithfulness, Answer Relevancy, Context Utilization qua Ollama.
  Không công bố context recall/answer correctness khi thiếu đáp án độc lập.
- Bộ 7 câu `chatbot_smoke.jsonl` là fixture chạy thử, chưa phải bộ nghiệm thu.
- API collect đi qua luồng chatbot bình thường, có thể lưu lịch sử của admin.
- Không chuyển corpus hoặc các báo cáo thực nghiệm cũ của PHUC.

```powershell
# Dùng môi trường có dependencies API. RAGAS chỉ cần ở bước score.
python -m pip install -r apps/api/requirements.txt -r eval/requirements-ragas.txt
# Đặt ADMIN_ACCESS_TOKEN bằng token của admin; runner không ghi token vào báo cáo.
python eval/ragas_eval.py --phase collect --api-url http://localhost:8000
python eval/ragas_eval.py --phase score --judge-model TEN_MODEL_OLLAMA
```

Chấm bằng cùng họ model với model sinh có thể thiên lệch; cần nêu rõ judge trong báo cáo.
Các file kết quả và bản sao DB để kiểm thử nằm ngoài Git.

### Corpus và điều kiện chạy thực nghiệm

Corpus có sẵn trong `apps/api/chatbot_corpus` của feature dùng manifest có cả hash
LF và CRLF. Indexer chỉ chấp nhận khác biệt xuống dòng do Git trên Windows, vẫn
từ chối thay đổi nội dung và kiểm tra toàn bộ bundle trước khi ghi DB. Không sửa
manifest để bỏ qua checksum. Nạp vào schema riêng `legal_ctu_v1` bằng:

```powershell
docker compose exec api python -m app.room_service.legal_knowledge.index_corpus
```

Đã nạp thành công trên môi trường hiện tại: 45 tài liệu, 571 đoạn và 571 vector
E5 thật; không nhập corpus khác ngoài bundle vốn có của feature.

Không sao chép `.env` hoặc khóa API PHUC. Trước khi đo chất lượng, cần kiểm tra
model sinh của feature đã cấu hình và model Ollama dùng để chấm đã sẵn sàng.
Chưa chạy lượt RAGAS chấm thật, chưa có số liệu độ chính xác để công bố.

`recommendation_eval.py` tái sử dụng P@K/NDCG@K với nhãn manual/student_survey/
held_out_interaction. Giữ nguyên các notebook matching và recommendation của feature.

Risk Detection tạm hoãn trong nhánh `NCKH/NEW`: đã bỏ nhãn/điểm rủi ro trên giao diện,
màu bản đồ theo điểm rủi ro và runner đánh giá risk. Chatbot không đọc điểm rủi ro để
xếp hạng hoặc sinh câu trả lời. Giữ các cột DB và trường response cũ với giá trị trung
tính để tương thích, không cần migration xóa dữ liệu. Báo cáo và kiểm duyệt thủ công
vẫn hoạt động độc lập. File nhãn recommendation mẫu chỉ minh họa cấu trúc, bị runner
từ chối khi còn nhãn synthetic.

```powershell
python eval/recommendation_eval.py --dataset DU_LIEU_DA_GAN_NHAN.jsonl --k 10
```

Kiểm thử PostgreSQL yêu cầu `FEEDBACK_TEST_DATABASE_URL` kết thúc bằng `_test`.
Bộ kiểm thử từ chối chạy trên DB ứng dụng.

## Kết quả xác minh lần chuyển

- 37 kiểm thử đạt; 2 expected failures ghi nhận giới hạn sentiment với câu không
  dấu và câu phủ định. Các trường hợp này không được tính là đã sửa thành công.
- Build web thành công. API, trang chi tiết và các trang admin render được.
- Endpoint admin trả 200 cho admin, 403 khi chưa xác thực.
- Kiểm tra SQL thật trên DB `_test`: chặn tự đánh giá/trùng; báo cáo mới không
  tự sửa risk; ẩn/duyệt báo cáo; bác báo cáo không khôi phục tin đã ẩn.
- Không chuyển risk engine, không huấn luyện model phân loại lừa đảo.
