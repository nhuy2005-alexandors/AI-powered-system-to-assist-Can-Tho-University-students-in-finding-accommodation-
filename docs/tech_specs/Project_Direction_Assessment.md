# Đánh giá Toàn Dự Án — Hướng Đi & Lệch Hướng

> Ngày: 2026-07-03 · Người đánh giá: Claude Code (Opus, orchestrator)
> Phương pháp: đọc tài liệu định hướng gốc (SRS/Roadmap/Sprint_Plan/04_BaiToanAn) +
> map trạng thái code THẬT (endpoint, schema, crawler, AI, frontend, test, eval).
> Mục đích: chỉ ra dự án có đi đúng hướng khoa học của đề tài NCKH không, lệch chỗ nào.

---

## 0. TL;DR (kết luận thẳng)

**Nền tảng kỹ thuật vững, đúng thứ tự — NHƯNG phần lõi khoa học (AI) chưa bắt đầu.**

- ✅ Data Engineering (crawler đa nguồn + làm sạch + phân loại + geocode + freshness) làm tốt,
  đúng ưu tiên "T1 trước — hệ thống chết nếu bỏ crawler".
- ✅ Auth, CRUD, search, frontend cơ bản chạy thật, verified.
- ❌ **4 module AI (Recommendation, RAG Chatbot, Roommate Matching, Risk Detection) = 0% code.**
  Đây chính là phần "cao hơn website CRUD" mà đề tài tuyên bố là giá trị khoa học.
- ⚠️ Một số **lệch logic** đang hiển thị sai cho người dùng (badge rủi ro giả — mục 3.1).

Chưa lệch hướng chiến lược (đúng theo Sprint_Plan: AI ở S3/S4). **Rủi ro là timeline + việc
novelty chưa được chứng minh bằng số liệu** — vốn là điều kiện nghiệm thu NCKH.

---

## 1. Hướng đi đề tài (theo tài liệu gốc)

Đề tài THS2026-66: "Hệ thống tổng hợp & gợi ý nhà trọ ứng dụng AI cho SV ĐH Cần Thơ".

**Novelty tuyên bố** (`01_DanhGia_Va_DinhHuong`): mô hình **AI-Powered Aggregator** —
crawl 80% data + AI làm giàu (chuẩn hóa, dedup, risk) + AI phục vụ (gợi ý, ở ghép, chatbot RAG)
+ cộng đồng xác nhận 20%. Giá trị khoa học = **Data Science + Data Engineering + AI**, không
phải CRUD web. Giải "chicken-and-egg" (không user → không data → không gợi ý) bằng crawler.

**Yêu cầu nghiệm thu định lượng** (Roadmap P4 "mọi module AI phải có metric"): Precision@10 ≥0.6,
ILS ≤0.7, dedup recall ≥90%, geocode ≥80% medium+, RAGAS Faithfulness ≥0.7, risk detection đo được.

## 2. Trạng thái thật vs kế hoạch (theo Sprint)

| Sprint | Kế hoạch | Thực tế | Trạng thái |
|--------|----------|---------|-----------|
| S0 | Khảo sát + setup + seed 100 + POI 500 | docker chạy; **chưa thấy POI/ward seed, chưa có form data** | ⚠️ một phần |
| S1 | Crawler + DB + Auth + search API | crawler 6 nguồn, cleaner, auth đa provider, search — **verified** | ✅ vượt (thêm UGC CRUD) |
| S2 | UI search/map + **Risk** + Freshness | UI list/detail có, freshness có; **map = placeholder, Risk = CHƯA** | ⚠️ dở dang |
| S3 | Recommendation + Roommate + eval | **0% — chỉ có cột vector rỗng + eval stub** | ❌ chưa |
| S4 | Chatbot RAG + UGC + Admin | UGC CRUD xong; **RAG/Admin = 0%** | ❌ chủ yếu chưa |
| S5 | Test + deploy + báo cáo | 86 test (auth/crawler/cleaner/CRUD); chưa pen-test/user-test | ⏳ chưa tới |

**Vị trí hiện tại: giữa S1→S2.** S1 làm tốt và vượt yêu cầu (đã có UGC CRUD của S4). Nhưng
S2 mới nửa chừng và **toàn bộ khối AI (S3/S4) — lõi khoa học — chưa chạm.**

## 3. LỆCH LOGIC đang tồn tại (cần sửa)

### 3.1 Badge rủi ro GIẢ — nghiêm trọng nhất
- FE detail + card hiển thị badge `risk_level` (safe/caution/suspicious).
- Nhưng `risk_score` trong DB **luôn = 0** (DEFAULT) — **không có code nào tính risk.**
  Không có IsolationForest, không rule-based (FR-7 / T10 / bài toán ẩn 7 chưa làm).
- Hệ quả: mọi tin hiện "safe" (score 0 < 0.3) → **người dùng thấy badge "an toàn" cho tin
  CHƯA hề được kiểm rủi ro.** Đây là hiển thị sai lệch, có thể gây hiểu nhầm nguy hiểm
  (đúng thứ đề tài muốn chống — tin lừa đảo).
- **Khuyến nghị:** hoặc ẩn badge tới khi có risk engine, hoặc gắn nhãn "chưa đánh giá"
  cho risk_score=0 thay vì "safe".

### 3.2 Cột/bảng AI rỗng nhưng schema đã tạo
- `embedding_vector`, `preference_vector`, `matching_vector` (VECTOR 384) — tạo, chưa bao giờ ghi/đọc.
- Bảng `roommate_profiles`, `match_requests`, `user_interactions`, `saved_searches`, `reports`
  — tạo, **không có code nào tham chiếu.** Schema stub cho tương lai.
- Không lệch (đúng kế hoạch chuẩn bị trước), nhưng cần biết: chưa có index vector (ivfflat/hnsw)
  → khi làm AI phải thêm.

### 3.3 Classifier lọt nhiều 'khac'
- mogi/nhadatcantho247 nhiều tin rơi `listing_type='khac'` → bị ẩn khỏi search phòng trọ.
  (đã ghi ở `Data_Cleaning_Pipeline_Design.md`). Mất một ít data hợp lệ.

### 3.4 Map chưa thật (FR-2.4)
- `/map` hiện là danh sách sắp theo khoảng cách, không phải bản đồ Leaflet tương tác.
  FR-2.4 + T3 yêu cầu Leaflet. Placeholder có chủ đích (tránh rủi ro build), nhưng là nợ.

## 4. Lệch so với TÀI LIỆU (không phải lỗi, nhưng cần chốt)

1. **Backend stack:** doc `03_ThietKe` nói 2 service (Node/Express + FastAPI). Thực tế **1 FastAPI**.
   → Đây là quyết định ĐÚNG (đơn giản, ít chỗ hỏng). Nên cập nhật doc về 1 backend, bỏ Node.
2. **Nguồn crawl:** kế hoạch Phongtro123/Chotot/Mogi. Thực tế Chotot **DEAD** (Cloudflare) → thay
   bds123 + nhadatcantho + nhadatcantho247. Đúng tinh thần "parser plugin dễ thay nguồn". OK.
3. **6 mâu thuẫn nội bộ giữa tài liệu cũ (02/03/04) và bản mới 29/06 (SRS/Roadmap/Sprint):**
   Gemini 1.5 vs 2.0; dedup 75% vs Jaccard 0.8; matching weight (ngành học 10% tổng 85% vs
   noise 15% tổng 100%); tần suất crawl (6-12h vs 6h vs 5h+3am); lịch sprint lệch mốc.
   → **Chốt bộ ba mới (SRS/Roadmap/Sprint_Plan 29/06) làm chuẩn**, đánh dấu 02/03/04 là "tham khảo".

## 5. Điểm LÀM TỐT (giữ nguyên hướng)

- **Thứ tự ưu tiên đúng:** crawler (T1) trước, đúng lời "hệ thống chết nếu bỏ T1". Data có
  trước thì AI mới có cái để học — không rơi vào chicken-and-egg.
- **Data đã chuẩn bị SẴN cho AI:** `quality_score` + `listing_type` + geocode + `parsed_amenities`
  → khi làm recommendation, đã có tập sạch + đặc trưng để vector hóa. Đây là bước đi thông minh.
- **Nguyên tắc P2 (không xóa, chỉ ẩn)** tôn trọng: soft-delete 'hidden', 'expired' giữ row.
- **Bảo mật đúng NFR:** bcrypt, JWT 15p/refresh, httpOnly cookie chống XSS, SQL param-bound.
- **Test 86 ca** cho phần đã làm — kỷ luật tốt (dù chưa đạt mốc ≥60% coverage toàn hệ).

## 6. RỦI RO lớn nhất (khoa học, không phải kỹ thuật)

Đề tài NCKH được đánh giá bằng **novelty AI + số liệu định lượng**. Hiện tại:
- Sản phẩm nếu dừng ở đây = "web tổng hợp tin trọ có crawler" — **đúng thứ đề tài nói là KHÔNG đủ**
  ("cao hơn việc chỉ viết website CRUD").
- `eval/` harness là **stub**: notebook 01 `raise NotImplementedError`, thiếu file ground-truth,
  chưa đo được gì. Trong khi nghiệm thu cần Precision@10, RAGAS, dedup recall...
- **4 tháng còn lại (S3/S4/S5)** phải làm: recommendation + RAG + matching + risk + eval + báo cáo.
  Đây là phần khó nhất và chưa bắt đầu.

## 7. KHUYẾN NGHỊ thứ tự (giảm rủi ro khoa học)

1. **Vá lệch logic ngay (nhanh):** sửa badge rủi ro giả (3.1) — hoặc ẩn, hoặc nhãn "chưa đánh giá".
2. **Risk Detection (S2, T10)** — làm sớm vì: (a) đang hiển thị sai, (b) rule-based đơn giản
   (không ảnh, giá bất thường, từ khóa "đặt cọc trước") cho kết quả nhanh, (c) là 1 trong 4 AI module.
3. **Recommendation (S3, T5)** — lõi novelty nhất. Data đã sẵn (quality_score + amenities + distance).
   Content-Based + Cosine + preference_vector. Đo Precision@10 ngay để có số cho báo cáo.
4. **Kích hoạt eval harness thật** song song với mỗi module AI — không để dồn cuối.
5. **RAG Chatbot (S4)** — sau khi có recommendation, tái dùng embedding.
6. Chốt lại tài liệu (mục 4) để nhóm không hiểu nhầm scope.

## 8. Kết luận

Dự án **không lệch hướng chiến lược** — đang xây nền đúng thứ tự, data sạch đã sẵn cho AI.
Nhưng **đang ở ngã rẽ quan trọng**: phần đã làm (crawler/CRUD/auth/UI) là "vé vào cửa", còn
**giá trị khoa học thật (AI + metric định lượng) vẫn nằm hoàn toàn phía trước và chưa bắt đầu.**
Ưu tiên tiếp theo nên là **Risk (vá lệch + AI module nhanh) → Recommendation (novelty lõi)**,
kèm eval đo số liệu, thay vì tiếp tục polish phần frontend/CRUD đã đủ dùng.
