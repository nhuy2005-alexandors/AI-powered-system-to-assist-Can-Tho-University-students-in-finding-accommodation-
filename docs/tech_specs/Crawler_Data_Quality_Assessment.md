# Đánh giá hướng cào & chất lượng dữ liệu Crawler

> Ngày: 2026-07-03 · Dựa trên 348 tin thực tế trong DB (324 cleaned / 14 rejected)
> Mục đích: đánh giá thẳng thắn xem data hiện tại có DÙNG ĐƯỢC cho mục tiêu (gợi ý trọ
> cho sinh viên ĐH Cần Thơ) hay không, và cần sửa gì trước khi xây frontend/AI.

## 1. Tóm tắt đánh giá (TL;DR)

Data **đủ để dựng frontend demo**, nhưng **chưa đủ chất lượng cho AI gợi ý nghiêm túc**.
Ba vấn đề gốc:

1. **Lệch đối tượng** — 2 nguồn (mogi, nhadatcantho247) hầu hết là nhà nguyên căn / mặt
   bằng kinh doanh, KHÔNG phải phòng trọ sinh viên.
2. **Diện tích không đáng tin** — 42.6% tin có diện tích do hệ thống *đoán* (imputed),
   không phải số thật từ nguồn.
3. **Một nguồn địa chỉ rác** — bds123 lấy nhầm banner làm địa chỉ.

## 2. Đánh giá theo từng nguồn

| Nguồn | Số tin | Đánh giá | Ghi chú |
|-------|--------|----------|---------|
| **phongtro123** | 235 | ⭐ Tốt nhất | Đúng đối tượng (trọ), địa chỉ + quận + toạ độ đầy đủ 235/235. Xương sống của hệ thống. |
| **tromoi** | 18 | ✅ Khá | Chuyên trọ/phòng, data sạch, toạ độ đủ. Ít tin. |
| **bds123** | 9 | ⚠️ Địa chỉ hỏng | Đúng đối tượng (trọ) nhưng selector địa chỉ trang chi tiết bắt nhầm "Xin chào Khách". Toạ độ hiện là fallback cấp quận. |
| **mogi** | 30 | ❌ Lệch đối tượng | 83% (19/23) là nhà mặt tiền / nguyên căn, giá TB 6.5tr — không phải trọ SV. |
| **nhadatcantho247** | 19 | ❌ Lệch + thiếu quận | 84% (16/19) off-target, giá TB 5.8tr, 14/19 thiếu quận. |
| **nhadatcantho** | 2 | ❓ Chưa đủ mẫu | Mới sửa URL, cần crawl full mới đánh giá được. |

## 3. Các chỉ số chất lượng (đo thực tế)

### 3.1 Diện tích — điểm yếu lớn nhất
- **138/324 tin (42.6%) có diện tích là ĐOÁN** (`is_imputed_area=true`).
- Cơ chế đoán: nếu không tìm thấy số m² trong mô tả → suy theo bậc giá (giá < 1tr → 15m²,
  < 1.5tr → 20m², ...). Đây là **giả định thô**, sai số lớn.
- Hệ quả: bộ lọc "diện tích ≥ X m²" và gợi ý AI dựa trên diện tích sẽ **không đáng tin**
  cho gần nửa số tin. Cần đánh dấu rõ "diện tích ước tính" trên UI.

### 3.2 Đối tượng (target fit) — 32% lệch
Đếm tin có tiêu đề chứa "nhà / mặt bằng / mặt tiền / nguyên căn / kho / văn phòng / kinh doanh":

| Nguồn | Off-target | Tỉ lệ |
|-------|-----------|-------|
| mogi | 19/23 | **83%** |
| nhadatcantho247 | 16/19 | **84%** |
| phongtro123 | 70/231 | 30% (*) |
| tromoi | 8/18 | 44% (*) |

(*) Con số phongtro123/tromoi bị thổi phồng do regex bắt cả cụm "**nhà** trọ" — cần kiểm tra
thủ công. Nhưng mogi & nhadatcantho247 thì lệch thật: đó là site bất động sản tổng hợp,
không chuyên trọ.

**Khuyến nghị:** thêm một tầng lọc đối tượng (loại tin giá > ~5tr HOẶC tiêu đề rõ là
nhà nguyên căn/mặt bằng), hoặc đổi URL nguồn mogi/nhadatcantho247 sang đúng chuyên mục
phòng trọ nếu site có.

### 3.3 Phân bố giá — hợp lý cho phân khúc SV
- 70% tin nằm trong khoảng **1–3.5 triệu/tháng** — đúng túi tiền sinh viên.
- Đuôi > 8tr (30 tin) gần như trùng với nhóm off-target ở 3.2.
- Bộ lọc reject hiện tại (< 400k hoặc > 20tr) quá rộng — lọt nhiều nhà 6–15tr.

### 3.4 Geocode (lên bản đồ)
- medium 172 · high 144 · low 5 · **failed 27** (7.8%).
- 27 tin failed = không lên bản đồ / không tính được khoảng cách tới CTU.
- Nhiều tin "high" thực chất là fallback cấp quận (nhãn lạc quan hơn độ chính xác thật).

### 3.5 Trùng lặp
- 348 tin / 311 content_hash duy nhất → có ~37 tin nội dung na ná (khác nguồn hoặc
  đăng lại). Dedup MinHash chỉ chạy trong 1 batch cào, **không** so với data cũ trong DB
  → trùng chéo-lần-cào lọt lưới. Chưa nghiêm trọng ở quy mô này.

## 4. Đánh giá HƯỚNG CÀO (chiến lược)

**Điểm đúng:**
- Chọn site chuyên trọ (phongtro123, tromoi, bds123) làm nòng cốt là hướng đúng.
- Kiến trúc JSON-selector cho phép thêm nguồn nhanh, không sửa code.
- Rate-limit 5s + xoay User-Agent: lịch sự, ít bị chặn.
- Batch near-fresh (5h/lần) hợp lý — trọ không đổi theo phút.

**Điểm sai / cần chỉnh:**
- **Gom nhầm site tổng hợp BĐS** (mogi, nhadatcantho, nhadatcantho247) — các site này bán
  cả nhà/đất/mặt bằng, làm loãng data. Nên trỏ đúng chuyên mục "phòng trọ" của từng site,
  hoặc bỏ nếu không có chuyên mục.
- **Phụ thuộc geocode ngoài (Nominatim)** cho địa chỉ Việt Nam vốn nhiễu → 7.8% fail +
  nhiều tin chỉ chính xác cấp quận. Cân nhắc bảng landmark/ward nội bộ mạnh hơn.
- **Đoán diện tích theo giá** là giải pháp tình thế — nên ưu tiên lấy diện tích thật từ
  trang chi tiết thay vì đoán.

## 5. Việc nên làm (ưu tiên giảm dần)

1. **Sửa bds123 selector địa chỉ** (đang lấy banner) — nhanh, tác động rõ.
2. **Thêm tầng lọc đối tượng** loại nhà/mặt bằng khỏi mogi/nhadatcantho247, hoặc đổi URL nguồn.
3. **Ưu tiên diện tích thật** từ detail page; chỉ đoán khi thật sự không có, và luôn gắn cờ
   "ước tính" cho UI/AI biết.
4. Siết ngưỡng reject giá theo phân khúc trọ (vd cảnh báo/loại > 6tr).
5. (Sau) Dedup so với DB, không chỉ trong batch.

## 6. Kết luận

Data **dùng được để demo frontend** (hiển thị danh sách, bản đồ, chi tiết) — nòng cốt
phongtro123 + tromoi + bds123 sạch và đúng đối tượng. Nhưng **trước khi làm AI gợi ý**,
cần xử lý lệch-đối-tượng (mogi/nhadatcantho247) và độ tin cậy diện tích, nếu không mô hình
sẽ học trên data nhiễu và gợi ý sai (vd gợi ý nhà 12tr cho sinh viên).
