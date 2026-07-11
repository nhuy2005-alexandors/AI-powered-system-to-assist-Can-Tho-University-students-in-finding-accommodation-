# 📑 TÀI LIỆU 4: PHÂN TÍCH CÁC BÀI TOÁN ẨN VÀ HƯỚNG GIẢI QUYẾT
**Đề tài:** Hệ thống tổng hợp và gợi ý nhà trọ ứng dụng AI — THS2026-66

> Tương tự cách bài toán "Dữ liệu Real-time" được phân tích, tài liệu này đào sâu vào **những rủi ro kỹ thuật tiềm ẩn** mà nhóm sẽ gặp phải khi bắt tay implement từng chức năng.

---

## BÀI TOÁN ẨN SỐ 1 — RECOMMENDATION: "COLD START" CHO NGƯỜI DÙNG MỚI

### Nghịch lý:
> AI Content-Based Filtering cần biết sở thích của sinh viên để gợi ý.
> Nhưng sinh viên mới đăng ký chưa có **lịch sử tìm kiếm, hành vi click, hay hồ sơ đầy đủ**.

**Vấn đề cụ thể:**
- Sinh viên năm 1, mới vào trường, không biết mình muốn gì → Profile rỗng → AI không biết gợi ý gì.
- Gợi ý "ngẫu nhiên" ở màn hình đầu → Cảm giác hệ thống "vô dụng" ngay lần đầu dùng.
- Đây là điểm chết của hầu hết app Recommendation mới ra mắt.

**Giải pháp — 3 tầng:**

| Tầng | Khi nào áp dụng | Cách làm |
|---|---|---|
| **Tầng 0 (Onboarding)** | Lần đầu đăng ký | Bắt buộc điền 3 câu hỏi nhanh: Ngân sách? Khoảng cách đến CTU? Tiện ích bắt buộc? → Dùng làm vector khởi tạo |
| **Tầng 1 (Popularity-Based)** | Khi chưa có đủ hành vi | Gợi ý "Top 10 phòng được xem nhiều nhất tuần này" theo khu vực — không cần AI |
| **Tầng 2 (Implicit Feedback)** | Sau 5-10 lượt xem | Theo dõi **ẩn**: phòng nào xem > 30 giây, phòng nào bookmark, phòng nào click vào SĐT → Dần dần cập nhật vector người dùng |

**Bổ sung nghiên cứu:** Kỹ thuật này gọi là **Hybrid Cold-Start Strategy**, đã được áp dụng trong Netflix, Spotify. Cần dẫn chứng paper: *"A Survey of Cold-Start Problem in Collaborative Filtering"* (Zhang et al., 2021).

---

## BÀI TOÁN ẨN SỐ 2 — RECOMMENDATION: "FILTER BUBBLE" (BỌT LỌC)

### Nghịch lý:
> AI càng gợi ý đúng sở thích → Người dùng càng chỉ thấy một loại phòng → Bỏ lỡ phòng tốt hơn ở khu khác hoặc khoảng giá khác.

**Vấn đề cụ thể:**
- Sinh viên từng xem vài phòng giá 1.5 triệu ở khu X → AI chỉ gợi ý phòng giá 1.5 triệu khu X mãi.
- Trong khi có phòng 1.8 triệu ở khu Y, gần CTU hơn 500m, được review tốt hơn nhiều.
- AI bị "kẹt" trong không gian tìm kiếm hẹp → **Recommendation Diversity** thấp.

**Giải pháp — Kỹ thuật Epsilon-Greedy:**

```
Thay vì: Luôn chọn Top-K phòng giống nhất nhất (Exploitation)
Áp dụng: 80% Top-K phù hợp nhất + 20% phòng ngẫu nhiên ngoài vùng thoải mái (Exploration)
```

- Thêm tính năng **"Khám phá thêm"** (Explore tab): Gợi ý phòng có điểm review cao nhưng nằm ngoài tiêu chí thông thường của user.
- Đo lường bằng chỉ số **ILS (Intra-List Similarity)** — Càng thấp = Gợi ý càng đa dạng, tốt.

---

## BÀI TOÁN ẨN SỐ 3 — ROOMMATE MATCHING: "NGƯỜI DÙNG KHAI SAI HỒ SƠ"

### Nghịch lý:
> Thuật toán Weighted Cosine Similarity hoạt động dựa trên dữ liệu hồ sơ sinh viên.
> Nhưng khi tự khai, người ta khai **hình mẫu lý tưởng của mình**, không phải **thực tế**.

**Vấn đề cụ thể:**
- Sinh viên khai "Mức độ dọn dẹp: Rất sạch sẽ" nhưng thực tế cả tuần không quét nhà.
- Khai "Giờ ngủ: Trước 11h" nhưng thực tế chơi game đến 2h sáng.
- Kết quả: AI ghép 2 người "tương thích trên giấy" nhưng thực tế không hòa hợp → **Người dùng mất niềm tin vào tính năng Matching**.

**Giải pháp:**

1. **Phương pháp "Khung bắt buộc chọn" (Forced Choice):** Thay vì điền text tự do, dùng câu hỏi kịch bản:
   > *"Bạn đang học bài lúc 11 giờ đêm thì bạn cùng phòng bật nhạc to. Bạn phản ứng thế nào?"*
   > ○ Nhờ tắt nhạc  ○ Tắt bớt một chút là OK  ○ Không quan tâm
   
   Câu hỏi tình huống khó bịa hơn câu hỏi mô tả bản thân.

2. **Cơ chế "Xác nhận sau khi ở ghép" (Post-Match Feedback):** Sau 2 tuần ở ghép, hỏi *"Bạn ở ghép có hài lòng không?"* → Dùng phản hồi này để **hiệu chỉnh lại mô hình** (điều chỉnh trọng số tính năng nào đang đoán sai).

3. **Tính "Social Proof":** Hiển thị review của những người đã ở ghép với người đó trước đây (nếu có).

---

## BÀI TOÁN ẨN SỐ 4 — CHATBOT RAG: "HALLUCINATION Ở VÙNG BIÊN"

### Nghịch lý:
> RAG sẽ trả về context là Top-5 phòng trọ liên quan nhất từ database.
> Nhưng nếu **không có phòng nào thỏa mãn câu hỏi**, hệ thống vẫn bơm Top-5 phòng "gần nhất" vào Prompt → LLM cố gắng trả lời bằng dữ liệu không liên quan → **Bịa ra thông tin sai**.

**Vấn đề cụ thể:**
- SV hỏi: *"Có phòng có bể bơi riêng không?"* → Database không có → RAG vẫn lấy 5 phòng ngẫu nhiên → Gemini bịa: *"Phòng tại đường X có hồ bơi..."*.
- SV hỏi giá phòng đã cho thuê tuần trước → Database đã cập nhật nhưng vector chưa re-index → Chatbot vẫn báo còn phòng.

**Giải pháp — Confidence Thresholding:**

```python
def safe_rag_answer(question: str, vectorstore, llm, threshold=0.65):
    # Lấy Top-5 chunks kèm điểm tương đồng
    results = vectorstore.similarity_search_with_score(question, k=5)
    
    best_score = results[0][1]  # Điểm cao nhất
    
    # Nếu không có chunk nào đủ liên quan → TỪ CHỐI, không bịa
    if best_score < threshold:
        return {
            "answer": "Tôi không tìm thấy thông tin phù hợp với câu hỏi của bạn. "
                      "Bạn có thể thử lại với tiêu chí khác, hoặc xem danh sách phòng "
                      "trực tiếp tại đây: [Link tìm kiếm]",
            "source": None,
            "confidence": "low"
        }
    
    # Chỉ khi có context đủ liên quan mới gọi LLM
    context = "\n".join([doc.page_content for doc, _ in results])
    answer = llm.invoke(f"Context: {context}\n\nCâu hỏi: {question}")
    
    return {"answer": answer, "confidence": "high"}
```

**Bổ sung:** Re-index vector database ngay sau mỗi lần Crawler cập nhật (dùng trigger trong PostgreSQL). Không để chatbot dùng dữ liệu cũ.

---

## BÀI TOÁN ẨN SỐ 5 — CHATBOT: HỘI THOẠI NHIỀU LƯỢT (MULTI-TURN)

### Nghịch lý:
> RAG cơ bản chỉ nhớ 1 lượt hỏi-đáp. Hội thoại thực tế thường có nhiều lượt kế tiếp.

**Vấn đề cụ thể:**
- SV: *"Có phòng nào gần CTU không?"* → Chatbot trả kết quả.
- SV: *"Cái nào rẻ hơn?"* → Chatbot **không hiểu "cái nào"** là cái nào vì RAG stateless → Trả lời sai hoặc trả về kết quả mới không liên quan.

**Giải pháp — Conversation Memory Buffer:**

```python
from langchain.memory import ConversationBufferWindowMemory

# Nhớ lại 5 lượt gần nhất
memory = ConversationBufferWindowMemory(k=5, return_messages=True)

# Chain có nhớ lịch sử
from langchain.chains import ConversationalRetrievalChain

chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=vectorstore.as_retriever(),
    memory=memory
)

# Sau lượt 1, memory tự lưu → Lượt 2 "cái nào rẻ hơn" được giải nghĩa đúng
chain.invoke({"question": "Cái nào rẻ hơn?"})
```

---

## BÀI TOÁN ẨN SỐ 6 — CRAWLER: ĐỊA CHỈ TIẾNG VIỆT KHÔNG CHUẨN

### Nghịch lý:
> Toàn bộ tính năng bản đồ, khoảng cách, và gợi ý theo khu vực đều phụ thuộc vào **Tọa độ GPS (lat/lng)** chính xác.
> Nhưng địa chỉ nhà trọ Việt Nam (đặc biệt là hẻm ở Cần Thơ) **cực kỳ khó geocode**.

**Vấn đề cụ thể:**
- *"Hẻm 26, đường 3/2, Ninh Kiều"* → Google Geocoding API trả về tọa độ sai cách 2km.
- *"Gần chợ Xuân Khánh"* → Không có tọa độ nào cả.
- *"KV X tổ Y phường Z"* → Cú pháp địa phương, Google không nhận diện được.
- Kết quả trên bản đồ hiển thị sai vị trí → Sinh viên đến sai địa điểm → Mất niềm tin.

**Giải pháp — Geocoding Pipeline đa tầng:**

```
Bước 1: Gửi địa chỉ nguyên gốc lên Google Maps Geocoding API
  → Nhận được? → Dùng kết quả, lưu confidence = "high"

Bước 2: Nếu confidence thấp → Dùng NLP trích xuất landmark gần nhất:
  "gần Chợ Xuân Khánh", "cách ĐH Cần Thơ 500m", "hẻm Lý Tự Trọng"
  → Geocode landmark thay vì địa chỉ đầy đủ, confidence = "medium"

Bước 3: Nếu vẫn thất bại → Geocode đến cấp Phường/Quận
  "Phường An Bình, Ninh Kiều" → Tọa độ trung tâm phường
  confidence = "low" → Hiển thị badge "Vị trí ước lượng" trên bản đồ

Bước 4: Hoàn toàn không geocode được → Ẩn khỏi bản đồ, chỉ hiện trong danh sách
```

**Lưu lại `geocode_confidence` trong DB để cảnh báo người dùng:**
```sql
ALTER TABLE aggregated_listings 
ADD COLUMN geocode_confidence VARCHAR(10); -- 'high'|'medium'|'low'|'failed'
```

---

## BÀI TOÁN ẨN SỐ 7 — CẢNH BÁO RỦI RO: KẺ GIAN HỌC CÁCH QUA MẶT

### Nghịch lý:
> Rule-based Risk Detection hoạt động dựa trên các quy tắc cố định.
> Kẻ gian có thể **học quy tắc và lách luật**.

**Vấn đề cụ thể:**
- Hệ thống cảnh báo "Không có ảnh" → Kẻ gian đăng ảnh lấy từ Internet.
- Hệ thống cảnh báo "Giá quá thấp" → Kẻ gian đặt giá bình thường nhưng đòi "phí dịch vụ" qua kênh khác.
- Hệ thống chặn tin trùng lặp → Kẻ gian paraphrase lại mô tả đủ để qua MinHash.

**Giải pháp — Defense in Depth (Phòng thủ đa lớp):**

| Lớp | Kỹ thuật | Bắt được gì |
|---|---|---|
| **Lớp 1 (Rule-based)** | Quy tắc cứng: giá, ảnh, từ khóa | Tin lừa đảo thô |
| **Lớp 2 (Statistical)** | Isolation Forest theo khu vực + thời gian | Giá ảo tinh vi hơn |
| **Lớp 3 (Cross-platform)** | So sánh tin này với nguồn gốc trên Phongtro123 — nếu tin UGC nhưng ảnh trùng với tin crawl khu khác → Đỏ | Ảnh đánh cắp |
| **Lớp 4 (Community)** | Người dùng report → Nhiều report → Ưu tiên Admin kiểm tra | Hình thức lừa đảo mới |
| **Lớp 5 (Behavior)** | IP mới đăng nhiều tin cùng lúc, mô hình hành vi bất thường | Tài khoản spam farm |

**Quan trọng nhất:** Không bao giờ tự động XÓA tin bị flagged. Chỉ **hiển thị cảnh báo** cho người dùng và đưa vào hàng chờ Admin kiểm tra. Tránh xóa nhầm tin hợp lệ.

---

## BÀI TOÁN ẨN SỐ 8 — CRAWLER: ANTI-BOT VÀ BẢO TRÌ DÀI HẠN

### Nghịch lý:
> Hệ thống phụ thuộc crawler để có dữ liệu.
> Nhưng crawler có thể bị chặn bất cứ lúc nào, và HTML thay đổi sẽ phá vỡ toàn bộ pipeline.

**Vấn đề cụ thể:**
- Phongtro123 phát hiện bot → Block IP → **Toàn bộ nguồn dữ liệu chính bị ngắt**.
- Trang web đổi layout HTML → CSS selector cũ không còn hoạt động → Parser trả về `None` hết → DB không cập nhật mà không báo lỗi.
- Tháng 3 nhóm xây crawler xong, Tháng 6 báo cáo Phongtro123 đã thay đổi → Crawler "âm thầm chết".

**Giải pháp:**

1. **Rate limiting & Rotation:** Chỉ crawl 1 request/5 giây, xoay vòng User-Agent string, dùng danh sách IP Proxy nếu cần.

2. **Health Check tự động:**
```python
# Mỗi 6h sau khi crawler chạy xong:
def check_crawler_health(source: str, expected_min_records: int = 10):
    """Nếu crawl được ít hơn 10 bản ghi → Gửi email/Telegram cảnh báo cho nhóm."""
    new_count = db.query("SELECT COUNT(*) FROM aggregated_listings 
                          WHERE source=%s AND first_seen > NOW() - INTERVAL '7h'", source)
    
    if new_count < expected_min_records:
        send_alert(f"⚠️ Crawler {source} có thể đã chết! Chỉ crawl được {new_count} bản ghi.")
```

3. **Lưu raw HTML backup:** Lưu lại HTML thô trước khi parse. Nếu parser hỏng, có thể re-parse từ HTML backup mà không cần crawl lại.

4. **Thiết kế Parser dạng Plugin:** Mỗi nguồn có file config riêng `phongtro123_selectors.json` thay vì hard-code trong Python. Khi trang đổi layout, chỉ cần sửa file JSON, không cần sửa code.

---

## BÀI TOÁN ẨN SỐ 9 — FRESHNESS: TIN CÒN TRÊN WEB NHƯNG ĐÃ CHO THUÊ THỰC TẾ

### Nghịch lý:
> Chủ trọ thường lười gỡ tin sau khi đã cho thuê.
> Hệ thống thấy tin vẫn tồn tại trên Phongtro123 → Đánh dấu "Active" → Gợi ý cho sinh viên.
> Sinh viên liên hệ → "Hết phòng rồi em ơi" → **Trải nghiệm tệ**.

**Vấn đề cụ thể:**
- 40-60% tin trên các trang rao vặt là tin đã hết nhưng chưa gỡ (theo khảo sát người dùng Chợ Tốt 2023).
- Đây là lý do chính sinh viên bất mãn với Phongtro123 hiện tại.

**Giải pháp — Probabilistic Freshness Model:**

```
Score "Tin có thể còn phòng" = f(
  + Tin mới đăng trong 7 ngày trước → Xác suất cao
  + Tin có giá thị trường bình thường → Xác suất cao
  + Nhiều view nhưng chưa ai click SĐT → Có thể hết (tin trưng ra để kéo view)
  + User báo cáo "Đã liên hệ, hết phòng" → Xác suất thấp mạnh
  + Tin hơn 30 ngày, không update, không có view mới → Xác suất thấp
)
```

- Hiển thị rõ cho sinh viên: **"Cập nhật 3 ngày trước · Khả năng còn phòng: Cao"** hoặc **"⚠️ Tin cũ hơn 30 ngày, xác nhận trước khi liên hệ"**.
- **Cho phép sinh viên đánh dấu 1 click:** *"Tôi đã liên hệ → Hết phòng"* — Không cần đăng nhập, chỉ 1 click → Cập nhật ngay vào Freshness Score.

---

## BÀI TOÁN ẨN SỐ 10 — CHI PHÍ API BẢN ĐỒ VÀ DỮ LIỆU KHÔNG GIAN

### Nghịch lý:
> Tích hợp bản đồ và các chỉ số an sinh (khoảng cách đồn công an, bệnh viện) giúp AI thông minh hơn.
> Nhưng dùng Google Maps API cho mỗi bản ghi crawl về sẽ **đốt sạch ngân sách miễn phí** chỉ trong vài ngày.

**Vấn đề cụ thể:**
- Google Places API tính phí ~$32/1000 requests. 
- Tính toán khoảng cách (Distance Matrix API) cũng tốn phí tương đương. 
- NCKH sinh viên không có ngân sách duy trì hàng tháng cho việc này.

**Giải pháp — OpenStreetMap + PostGIS Local Computation:**

1. **Dùng Overpass API (Miễn phí):** Tải toàn bộ tọa độ đồn công an, trạm y tế, siêu thị... của Cần Thơ về DB nội bộ một lần duy nhất (Seed Data).
2. **Dùng PostGIS:** Tính khoảng cách trực tiếp trong PostgreSQL bằng hàm `ST_DWithin` hoặc `ST_DistanceSphere`.
3. **Chỉ dùng Map API ở Frontend:** Chỉ gọi API hiển thị bản đồ ở phía người dùng cuối (ưu tiên dùng Leaflet + OpenStreetMap Mapbox để miễn phí 100%).

---

## 📊 TỔNG HỢP: BẢN ĐỒ RỦI RO (10 BÀI TOÁN)

| # | Bài Toán Ẩn | Tính Năng Ảnh Hưởng | Mức Độ Nguy Hiểm | Độ Khó Giải |
|---|---|---|---|---|
| 1 | Cold Start — Người dùng mới | Recommendation | 🔴 Cao | 🟡 Trung bình |
| 2 | Filter Bubble — Gợi ý đơn điệu | Recommendation | 🟡 Trung bình | 🟢 Thấp |
| 3 | Người dùng khai sai hồ sơ | Roommate Matching | 🔴 Cao | 🟡 Trung bình |
| 4 | RAG Hallucination ở vùng biên | Chatbot | 🔴 Cao | 🟢 Thấp |
| 5 | Multi-turn conversation | Chatbot | 🟡 Trung bình | 🟢 Thấp |
| 6 | Địa chỉ tiếng Việt khó geocode | Bản đồ / Gợi ý | 🔴 Cao | 🔴 Khó |
| 7 | Kẻ gian học cách qua mặt | Cảnh báo rủi ro | 🟡 Trung bình | 🟡 Trung bình |
| 8 | Crawler bị chặn / layout đổi | Toàn hệ thống | 🔴 Cao | 🟡 Trung bình |
| 9 | Tin "chết trên thực tế" nhưng vẫn Active | Recommendation / Freshness | 🔴 Cao | 🟡 Trung bình |
| 10| Chi phí API Bản đồ quá tải | Dữ liệu không gian | 🔴 Cao | 🟡 Trung bình |

### Thứ tự ưu tiên giải quyết trong 6 tháng:
1. 🔴 **Bài toán 8 (Crawler)** — Hệ thống chết nếu bỏ qua bài này.
2. 🔴 **Bài toán 6 (Geocoding)** — Bản đồ sai = Toàn bộ tính năng vị trí sai.
3. 🔴 **Bài toán 10 (Chi phí API)** — Tránh "sập tiệm" trước khi bảo vệ đề tài.
4. 🔴 **Bài toán 1 (Cold Start)** — Ấn tượng đầu tiên của người dùng.
5. 🔴 **Bài toán 4 (RAG Hallucination)** — Chatbot bịa sẽ phá hỏng niềm tin.
6. 🔴 **Bài toán 9 (Freshness)** — Trực tiếp quyết định trải nghiệm người dùng.
7. 🟡 Các bài toán còn lại — Xử lý sau khi MVP hoạt động ổn định.
