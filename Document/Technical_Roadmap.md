# 🗺️ ROADMAP KỸ THUẬT — GIẢI QUYẾT CÁC BÀI TOÁN LỚN

**Đề tài:** Hệ thống tổng hợp & gợi ý nhà trọ ứng dụng AI — THS2026-66
**Phiên bản:** 1.0 · **Ngày:** 29/06/2026
**Phạm vi:** Tài liệu này gom các thách thức kỹ thuật cốt lõi, gắn mỗi thách thức với hướng giải, công nghệ, tiêu chí nghiệm thu (Definition of Done), sprint và người phụ trách. Nguồn tham chiếu: `Agent-Generated/04_PhanTich_BaiToanAn.md`, `03_ThietKe_KyThuat_Va_AI.md`, `02_PhanTich_NghiepVu_Va_DuLieu.md`.

---

## 0. NGUYÊN TẮC THIẾT KẾ

| # | Nguyên tắc | Lý do |
|---|---|---|
| P1 | Chi phí vận hành = 0đ trong thời gian đề tài | NCKH SV không có ngân sách hạ tầng định kỳ. Ưu tiên free tier + tính toán nội bộ. |
| P2 | Không bao giờ tự động XÓA dữ liệu (chỉ ẩn/cảnh báo) | Tránh xóa nhầm tin hợp lệ. Mọi quyết định destructive qua Admin. |
| P3 | AI từ chối khi không chắc chắn (fail-safe) | Thà không trả lời còn hơn bịa (Confidence Thresholding). |
| P4 | Mọi module AI phải có chỉ số đo lường định lượng | Yêu cầu khoa học cho nghiệm thu. Không demo cảm tính. |
| P5 | Parser/Crawler tách config khỏi code (plugin JSON) | Trang nguồn đổi layout → chỉ sửa JSON, không sửa code. |

---

## 1. BẢN ĐỒ THÁCH THỨC → SPRINT

| # | Bài toán lớn | Module | Mức nguy hiểm | Sprint giải | Người |
|---|---|---|---|---|---|
| T1 | Crawler bị chặn / layout đổi | Data Pipeline | 🔴 Cao | S1 | Phú |
| T2 | Geocoding địa chỉ tiếng Việt | Bản đồ/Spatial | 🔴 Cao | S1 | Huy |
| T3 | Chi phí API bản đồ | Spatial | 🔴 Cao | S0-S1 | Huy |
| T4 | Trùng lặp dữ liệu đa nguồn | Data Pipeline | 🟡 TB | S1 | Huy |
| T5 | Cold Start người dùng mới | Recommendation | 🔴 Cao | S3 | Phú |
| T6 | Filter Bubble (gợi ý đơn điệu) | Recommendation | 🟡 TB | S3 | Phú |
| T7 | Khai sai hồ sơ ở ghép | Roommate Matching | 🔴 Cao | S3 | Phú/Bảo |
| T8 | RAG Hallucination vùng biên | Chatbot | 🔴 Cao | S4 | Phú |
| T9 | Multi-turn conversation | Chatbot | 🟡 TB | S4 | Phú |
| T10 | Risk Detection bị qua mặt | Risk | 🟡 TB | S2 | Phú |
| T11 | Tin "chết" nhưng vẫn Active | Freshness | 🔴 Cao | S2 | Lợi |

> Thứ tự ưu tiên xử lý: T1 → T2/T3 → T4 → T11 → T5 → T8 → còn lại. Hệ thống chết nếu bỏ T1.

---

## 2. ĐẶC TẢ GIẢI PHÁP TỪNG THÁCH THỨC

### T1 — Crawler bị chặn / layout đổi 🔴

**Vấn đề:** HTTP 403/429 khi crawl; trang nguồn đổi HTML → parser trả null → pipeline chết âm thầm.

**Giải pháp 4 lớp:**
1. **Rate limit + rotation:** 1 request / 5 giây, xoay User-Agent, IP proxy nếu cần.
2. **Parser plugin JSON:** mỗi nguồn 1 file `<source>_selectors.json`, không hard-code CSS trong Python.
3. **Raw backup:** lưu HTML thô trước khi parse → re-parse offline khi layout đổi, không cần crawl lại.
4. **Health check tự động:** sau mỗi lần crawl, nếu `new_count < 10` → alert Telegram/email cho nhóm.

**Công nghệ:** Scrapy, `fake-useragent`, Telegram Bot API, cron 6h.

**DoD:**
- Crawl ≥3 nguồn (Phongtro123, Chotot, Mogi) không bị block trong 7 ngày liên tục.
- Layout 1 nguồn đổi → sửa JSON ≤15 phút, không sửa code.
- Alert gửi đúng khi crawl < ngưỡng.

---

### T2 — Geocoding địa chỉ tiếng Việt 🔴

**Vấn đề:** "Hẻm 26, đường 3/2", "gần Xuân Khánh", "KV X tổ Y phường Z" → Google trả sai 2km hoặc không nhận diện.

**Giải pháp pipeline 3 tầng:**
```
Tầng 1: Geocode địa chỉ đầy đủ (Nominatim/OSM)     → confidence = high
Tầng 2: NLP trích landmark ("gần Xuân Khánh"…)      → geocode landmark → medium
        → fallback geocode POI/đường đã biết
Tầng 3: Geocode cấp Phường/Quận (centroid)          → low
Thất bại hoàn toàn → geocode_confidence = 'failed', ẩn khỏi map view
```

**Công nghệ:** Nominatim self-host hoặc public (P1: tránh phí Google), spaCy/regex trích landmark, bảng `ward_centroids` seed sẵn 13 phường Ninh Kiều.

**DoD:**
- ≥80% listing đạt confidence ≥ medium.
- Badge "vị trí ước lượng" hiển thị khi confidence = low/failed.
- 0 listing hiển thị sai >1km trên 50 mẫu test thủ công.

---

### T3 — Chi phí API bản đồ 🔴

**Vấn đề:** Google Places ~$32/1000 req; Distance Matrix tương tự → vượt free tier sau vài trăm listing.

**Giải pháp "tính nội bộ":**
1. Tải POI 1 lần qua **Overpass API (OSM)**: đồn công an, bệnh viện, trạm bus quanh CTU → lưu bảng `poi_locations`.
2. Tính khoảng cách bằng **PostGIS `ST_Distance`** trên dữ liệu nội bộ, không gọi API runtime.
3. Bản đồ render bằng **Leaflet + OSM tiles** (miễn phí), không dùng Google Maps JS.

**Công nghệ:** PostGIS, Overpass API (chạy 1 lần), Leaflet.js.

**DoD:**
- Chi phí API bản đồ runtime = 0đ.
- Khoảng cách CTU/POI tính được cho 100% listing có toạ độ.

---

### T4 — Trùng lặp dữ liệu đa nguồn 🟡

**Vấn đề:** Cùng 1 phòng đăng trên nhiều trang, mô tả khác nhau → trùng listing.

**Giải pháp:** **MinHash + LSH** trên (tiêu đề + mô tả + giá + toạ độ làm tròn). Ngưỡng Jaccard ≥0.8 → coi là trùng, giữ bản `last_seen` mới nhất, gộp `source_url[]`.

**Công nghệ:** `datasketch` (MinHashLSH).

**DoD:**
- Dedup recall ≥90% trên tập 200 cặp trùng đã gán nhãn thủ công.
- False-merge rate ≤5%.

---

### T5 — Cold Start người dùng mới 🔴

**Vấn đề:** Content-Based cần profile, nhưng user mới chưa có hành vi → gợi ý rỗng/ngẫu nhiên → mất niềm tin lần đầu.

**Giải pháp lai 3 bước:**
1. **Onboarding Quiz 3 câu** (ngân sách, khoảng cách, tiện ích) → tạo `preference_vector` khởi tạo ngay.
2. **Bỏ qua quiz** → fallback **Popularity-Based** ("Top phổ biến tuần này").
3. Khi tích đủ implicit feedback (≥10 interaction) → chuyển hẳn sang Content-Based cá nhân hoá.

**Công nghệ:** Cosine Similarity, vector 384-dim, bảng `user_interactions`.

**DoD:**
- User mới luôn thấy ≥10 gợi ý có nghĩa ngay từ lần đầu (0 màn hình rỗng).
- Precision@10 ≥0.6 sau khi điền quiz (test trên 30 user-mock).

---

### T6 — Filter Bubble (gợi ý đơn điệu) 🟡

**Vấn đề:** Gợi đúng sở thích → user kẹt 1 loại phòng, bỏ lỡ lựa chọn tốt hơn.

**Giải pháp Epsilon-Greedy:** Top-K = **80% phù hợp nhất (exploitation) + 20% ngẫu nhiên ngoài vùng (exploration)**. Thêm tab "Khám phá" riêng.

**Công nghệ:** ε-greedy (ε=0.2), đo **Intra-List Similarity (ILS)** để định lượng diversity.

**DoD:**
- ILS ≤0.7 (càng thấp càng đa dạng).
- Tab Khám phá hiển thị ≥2 phòng khác khu/khác giá so với Top-K chính.

---

### T7 — Khai sai hồ sơ ở ghép 🔴

**Vấn đề:** User tự mô tả tính cách → khai đẹp, không thực → matching sai.

**Giải pháp:**
1. **Forced Choice (câu hỏi tình huống):** "Bạn cùng phòng bật nhạc 11h đêm, bạn sẽ?" → khó bịa hơn mô tả tự do.
2. **Post-Match Feedback:** sau 2 tuần ở ghép hỏi "hài lòng không?" → recalibrate trọng số.
3. **Social Proof:** hiển thị lịch sử ở ghép trước (nếu có).

**Công nghệ:** Weighted Cosine Similarity (trọng số: ngân sách 25%, giờ ngủ 20%, hút thuốc 15%, dọn dẹp 15%, tiếng ồn… ), threshold 0.7.

**DoD:**
- 6 câu Forced Choice → `matching_vector` 384-dim.
- MAE feedback sau 2 tuần ≤1.5/5 (trên tập thử nghiệm).

---

### T8 — RAG Hallucination vùng biên 🔴

**Vấn đề:** Câu hỏi không có dữ liệu liên quan → LLM bịa phòng không tồn tại.

**Giải pháp Confidence Thresholding:**
```python
results = vector_search(question, top_k=5)
if best_score < 0.65:
    return {"answer": "Không tìm thấy thông tin phù hợp. Thử tiêu chí khác nhé!",
            "confidence": "low", "source": None}
context = "\n".join(d.page_content for d in results)
answer = llm.invoke(f"Context: {context}\n\nCâu hỏi: {question}")
return {"answer": answer, "confidence": "high"}
```
Chỉ gọi LLM khi có context đủ liên quan. Re-index pgvector sau mỗi lần crawl.

**Công nghệ:** `multilingual-e5-small` (embed), pgvector, Gemini 2.0 Flash (fallback Llama 3.1 8B/Ollama nếu hết quota).

**DoD:**
- 0 hallucination trên 50 câu test (manual review).
- RAGAS Faithfulness ≥0.7, Answer Relevancy ≥0.75.
- Câu ngoài phạm vi → từ chối đúng cách.

---

### T9 — Multi-turn conversation 🟡

**Vấn đề:** "Cái nào rẻ hơn?" → bot không hiểu "cái nào" vì mất ngữ cảnh.

**Giải pháp:** **Conversation Memory 5 lượt** — nối lịch sử vào prompt; query rewriting (resolve tham chiếu "cái nào", "phòng đó" về entity cụ thể trước khi search).

**Công nghệ:** LangChain ConversationBufferWindowMemory (k=5).

**DoD:**
- 10 kịch bản multi-turn (hỏi nối tiếp) trả lời đúng tham chiếu ≥8/10.

---

### T10 — Risk Detection bị qua mặt 🟡

**Vấn đề:** Kẻ gian học cách lách → đặt giá bình thường, viết lại mô tả để qua MinHash.

**Giải pháp Defense in Depth (5 lớp):**

| Lớp | Kỹ thuật | Bắt được |
|---|---|---|
| 1 — Rule | Giá/ảnh/từ khoá cứng | Lừa đảo thô |
| 2 — Statistical | Isolation Forest theo khu vực + thời gian | Giá ảo tinh vi |
| 3 — Cross-platform | So ảnh UGC với tin crawl khác khu | Ảnh đánh cắp |
| 4 — Community | Nhiều report → ưu tiên kiểm tra | Hình thức mới |
| 5 — Behavior | Tài khoản mới đăng nhiều tin cùng lúc | Account farm |

**P2: không tự động xóa — chỉ hiển thị badge cảnh báo + giải thích lý do.**

**Công nghệ:** sklearn IsolationForest, perceptual hash (ảnh), bảng `reports`.

**DoD:**
- Recall ≥85% trên 100 tin lừa đảo gán nhãn ground truth.
- Mỗi badge có `risk_reasons[]` giải thích được.

---

### T11 — Tin "chết" nhưng vẫn Active 🔴

**Vấn đề:** Phòng đã cho thuê nhưng tin còn trên nguồn → user mất công liên hệ.

**Giải pháp Freshness Score:**
```
+ last_seen mới (crawler còn thấy)        → khả năng còn cao
- user báo "đã hết phòng"                  → giảm mạnh
- tin >30 ngày, không update               → giảm
```
Hiển thị: "Cập nhật 3 ngày trước · Khả năng còn phòng: Cao" hoặc "⚠️ Tin cũ >30 ngày".
**1-click report "Đã hết phòng"** (không cần đăng nhập) → cập nhật ngay.

**Công nghệ:** trigger cập nhật `freshness_score`, cột `status` ('active'|'stale'|'rented').

**DoD:**
- Tin >30 ngày tự gắn nhãn stale.
- 1-click report cập nhật score trong <2s.

---

## 3. PHỤ THUỘC GIỮA CÁC THÁCH THỨC

```
T1 (Crawler) ──┬──> T2 (Geocode) ──> T3 (Spatial) ──> hiển thị map
               ├──> T4 (Dedup)
               ├──> T10 (Risk)  ──> badge
               └──> T11 (Freshness)
                         │
T1 cấp data ──> embedding index ──> T8 (RAG) ──> T9 (Multi-turn)
                         │
user data ──> T5 (Cold Start) ──> T6 (Filter Bubble)
roommate data ──> T7 (Matching)
```
**Critical path:** T1 → (T2+T4+T10+T11) → index → T8. Nếu T1 trễ, toàn bộ trễ theo.

---

## 4. CHỈ SỐ NGHIỆM THU TỔNG HỢP (cho báo cáo khoa học)

| Module | Metric | Ngưỡng đạt |
|---|---|---|
| Crawler | Uptime 7 ngày, layout-change recovery | Không block, ≤15ph sửa |
| Geocoding | % confidence ≥ medium | ≥80% |
| Dedup | Recall / False-merge | ≥90% / ≤5% |
| Recommendation | Precision@10, NDCG@10, ILS | ≥0.6 / ≥0.65 / ≤0.7 |
| Roommate | MAE feedback 2 tuần | ≤1.5/5 |
| Chatbot RAG | Faithfulness, Answer Relevancy | ≥0.7 / ≥0.75 |
| Risk | Recall trên 100 tin scam | ≥85% |
| Freshness | Độ trễ cập nhật 1-click | <2s |

---

## 5. RỦI RO & FALLBACK

| Thách thức | Rủi ro còn lại | Fallback |
|---|---|---|
| T1 | 1 nguồn block vĩnh viễn | 2 nguồn dự phòng + manual seed 500 tin |
| T2 | Hẻm vẫn geocode kém | Badge "ước lượng" + ward centroid |
| T3 | Overpass đổi schema | Cache POI tĩnh trong repo |
| T8 | Hết quota Gemini | Llama 3.1 8B local qua Ollama |
| Tất cả AI | Dataset test quá nhỏ | Augment bằng crawl manual + mock user |

---

## 6. TRACKING

- Mỗi thách thức = 1 epic trên issue tracker.
- DoD = acceptance criteria của epic.
- Cập nhật trạng thái cuối mỗi sprint trong `Sprint_Plan.md`.
- Notebook evaluation lưu trong `NCKH/eval/` (Precision@K, RAGAS, ILS…).

