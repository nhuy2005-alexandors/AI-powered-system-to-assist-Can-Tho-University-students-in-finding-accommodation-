# Map & Routing

## Mục tiêu
Hiển thị tin trọ trên bản đồ tương tác, cho user chọn campus CTU (khu I/II/III) làm gốc,
và tính **thời gian đi thật theo đường sá** (không phải đường chim bay) từ tin tới campus —
precompute sẵn cho mọi tin để AI rank + hiển thị chính xác, hội đồng NCKH không bẻ được về
độ chính xác đề xuất.

## Glossary (thuật ngữ dùng xuyên spec)

**Lớp bản đồ nền**
- **Tile (raster tile)**: bản đồ nền chia ô ảnh vuông (256px), Leaflet tải + ghép. Đường/sông vẽ sẵn trong ảnh, mình mượn hiển thị, không host. Nguồn: OSM.
- **OSM (OpenStreetMap)**: data bản đồ mở, free. Tile nền + geocode + route đều ăn từ hệ này → khớp nhau.

**Lớp toạ độ**
- **Geocoding**: địa chỉ chữ → toạ độ số. "Hẻm 51 Trần Hoàng Na" → (10.03, 105.77).
- **Geocoder**: máy làm việc đó — `apps/api/app/crawler/geocode.py`, đa tầng (số nhà → phường → landmark → centroid), mỗi tầng 1 mức **confidence** (high/medium/low).
- **Nominatim**: service geocode free của OSM, giới hạn 1 req/s → phải cache tránh gọi trùng.

**Lớp khoảng cách / đường đi**
- **Haversine / đường chim bay**: khoảng cách thẳng 2 điểm. Rẻ nhưng bỏ qua sông/cầu → SAI nhiều ở Cần Thơ.
- **Route engine**: máy tính đường đi THẬT theo đường sá. Chọn **ORS (OpenRouteService)** — ăn cùng data OSM.
- **Route time vs route geometry**: *time* = "18 phút" (precompute, lưu cột, dùng rank + card); *geometry* = đường vẽ polyline (fetch khi click, không lưu sẵn).
- **Matrix endpoint**: API ORS trả 1 lúc nhiều cặp điểm→điểm. 1 call thay N call lẻ → dùng lúc backfill.
- **Precompute**: tính trước lúc INSERT, lưu cột, query sau chỉ đọc.

**Lớp DB không gian**
- **PostGIS**: extension biến Postgres thành DB hiểu toạ độ.
- **`geom`**: cột hình học lưu toạ độ (thay 2 cột lat/lng rời).
- **`ST_DWithin`**: hàm PostGIS "điểm nằm trong R mét không?", nhanh nhờ spatial index.
- **`geography`**: kiểu toạ độ tính mét thật trên mặt cầu (không phải độ).

**Lớp hiển thị (Leaflet FE)**
- **Marker / CircleMarker**: chấm đánh dấu 1 tin.
- **Popup**: bong bóng khi click marker.
- **Polyline**: đường gấp khúc nối toạ độ → vẽ route geometry.
- **Cluster**: gộp marker sát nhau thành 1 chấm số khi zoom xa (chưa cần, mới ~434 tin).
- **POI (Point of Interest)**: điểm đáng chú ý không phải trọ (trường/chợ/bến xe). **POI layer** = lớp marker riêng. Mầm có sẵn: dict `LANDMARKS` trong `geocode.py`.

## Yêu cầu
- [ ] FR-M.1 Bản đồ Leaflet + tile OSM, marker mỗi tin có toạ độ, popup giá + link chi tiết *(đã có, giữ)*
- [x] FR-M.2 **3 toạ độ campus thật** (khu I, II, III) — đã chốt (xem bảng Campus dưới)
- [ ] FR-M.3 Campus picker: user chọn khu → gốc tính khoảng cách đổi theo
- [ ] FR-M.4 Cột `route_time_campus[1,2,3]` (phút, route thật) precompute lúc upsert — như `distance_to_ctu`
- [ ] FR-M.5 Backfill route time cho tin đã có, qua ORS **Matrix endpoint** (batch, không N call lẻ)
- [ ] FR-M.6 Re-route khi user sửa address (piggyback vào path geocode `router.py:38`)
- [ ] FR-M.7 AI rank top-K bằng route time thật (không phải chim bay) → card hiện "X phút tới trường"
- [ ] FR-M.8 Route **geometry** (polyline) fetch on-demand khi user click 1 tin, không precompute
- [ ] FR-M.9 POI layer từ dict `LANDMARKS` có sẵn (trường/chợ/bến xe)

## Campus (gốc tính route — chốt 2026-07-06)
| Khu | Toạ độ (lat, lng) | Nguồn xác minh |
|---|---|---|
| Khu I | 10.0159, 105.7656 | Nominatim khớp "Trường Đại học Cần Thơ Khu 1, Đường 30 Tháng 4" |
| Khu II | 10.0322, 105.7683 | Nominatim khớp, trùng hằng số `geocode.py:24` |
| Khu III | 10.0340, 105.7798 | User cung cấp (01 Đ. Lý Tự Trọng, Khu 3, Ninh Kiều) — OSM không có node |

## Ràng buộc
- **Route engine = ORS**, ăn cùng data OSM như geocoder (Nominatim). KHÔNG Google (phí + lệch data source).
- Route TIME là số **tĩnh** (đường sá không đổi theo giờ) → lưu cột DB, **KHÔNG cache layer riêng (Redis)**. Cột DB chính là cache vĩnh viễn.
- Backfill KHÔNG đụng quota: Matrix nhận nhiều điểm/request (trần **3.500 locations/request**, verified [ORS restrictions](https://openrouteservice.org/restrictions/) 2026-07-06). 3 campus + 414 tin = 417 locations → cả backfill gói trong **1-2 call**, không phải 1302 call lẻ. Quota daily thành non-issue ở quy mô này.
- Chưa lấy được con số quota daily chính xác (trang plans ORS render rỗng, cần login dashboard = API key của user). Không chặn — vì backfill chỉ 1-2 call + steady-state vài tin/ngày, dưới mọi mức plausible. Xác nhận lại trên dashboard khi có key.
- Steady-state chỉ route tin MỚI mỗi lần crawl (vài tin) → cost tỉ lệ *tin mới*, không phải *tổng tin*.
- Chỉ route được tin đã có `geom` (coverage hiện tại ~95%, 414/434). Tin thiếu toạ độ không lên map — giới hạn geocode, không phải bug routing.
- **Trần độ chính xác geocode = cấp phường/đường, KHÔNG tới hẻm/số nhà.** OSM/Nominatim (đang dùng) không có data hẻm+số nhà ở Cần Thơ. String nguồn kiểu "hẻm 3 Hồ bún xáng gần ĐH Cần Thơ" (không phường, không số) là **vô-thông-tin** → không engine nào định vị chính xác được, kể cả trả tiền. Rác vào rác ra. Use case (SV lọc khu → đọc địa chỉ text gốc → gọi chủ trọ) KHÔNG đòi cấp số nhà → trần cấp-phường là ĐỦ.

## Quyết định
- **Precompute-all route time thay vì proxy chim bay + rerank**: dataset bé (domain trọ-quanh-CTU chặn phồng, trần vài nghìn tin active). Rank bằng metric thật = metric hiển thị → không lệch thứ tự, hội đồng không bẻ được. Rerank-sau-khi-route bị loại vì vẫn lọc top-K bằng chim bay TRƯỚC route → tin tốt theo đường thật bị loại sớm.
- **Route TIME precompute, route GEOMETRY on-demand**: time nhỏ (1 số/campus) tính sẵn được; geometry nặng (list toạ độ đường) chỉ cần khi user thật sự xem 1 tin.
- **List view KHÔNG route, chỉ AI-top-K + click mới route**: route N tin lúc render = N call vô nghĩa (user chưa chọn). Trigger route = (intent: click) HOẶC (tập nhỏ bounded: AI top 5/10). KHÔNG trigger theo nhãn nguồn "AI đề xuất" — nó chỉ là "tập nhỏ đã lọc". Cap N.
- **Cột DB thay cache**: route time tĩnh → không TTL, không invalidation theo giờ. Chỉ re-route khi address đổi (hiếm) hoặc thêm campus (vài năm/lần).
- **POI = reuse `LANDMARKS` dict có sẵn**, không đẻ bảng DB / crawl POI. Lên DB khi cần user tự thêm điểm.
- **KHÔNG hand-add landmark để cứu độ chính xác — bác bởi data (đếm 2026-07-06 trên 446 tin).** Mọi từ khoá tần suất cao đã được cover: "xuân khánh" 63 tin (đã có landmark + ward centroid), "nguyễn văn cừ" 37 / "3 tháng 2" 20 (đường lớn, Nominatim tự resolve). "Bún xáng" chỉ 4 tin — không đáng. Bug pin-in-school (tin gán đúng tâm CTU) hiện chỉ **1 tin**. Thêm landmark tay = churn, ROI thấp.
- **Budget path khi cần nâng độ chính xác: Goong (goong.io) TRƯỚC, Google SAU.** Vấn đề gốc = OSM thiếu data hẻm/số nhà VN, KHÔNG phải geocoder dở. Nếu đổ kinh phí: Goong = "Mapbox của VN", data đường/hẻm/số nhà VN tốt hơn OSM, rẻ hơn Google nhiều, API kiểu Google — lựa chọn budget đúng cho địa chỉ Cần Thơ. Google = chính xác nhất, đắt nhất, đổi ràng buộc P1 (cost=0). CẢ HAI vẫn thua string vô-thông-tin ("hẻm 3 Hồ bún xáng" không phường/số). **Chưa làm — use case hiện (SV lọc khu → đọc text gốc → gọi chủ) không đòi cấp số nhà.** Nâng khi UGC user tự đăng (địa chỉ đầy đủ hơn) hoặc hội đồng đòi.
- **SV tìm được trọ KHÔNG cần cấp số nhà**: luồng thật = lọc map theo khu (cấp landmark/phường đủ) → đọc **địa chỉ text gốc verbatim** (dân địa phương đọc là biết đường) → gọi chủ trọ hỏi → tới xem. Bắt buộc: card/popup PHẢI hiện address text gốc + nhãn confidence trung thực (pin low/medium = "vị trí tương đối", đừng giả vờ chính xác).

## Ngoài phạm vi
- Self-host OSRM (tải OSM extract VN + docker) — dùng ORS API free trước, add khi quota bung.
- Marker cluster — chưa cần ở ~434 tin, add khi đông tới mức chấm chồng.
- Map-first browse (kéo/zoom refetch theo viewport kiểu Airbnb) — đổi cả UX trang chủ, không thuộc phạm vi này.
- Logic AI chọn tin nào + tính điểm ra sao — **lane team AI**, spec này chỉ lo map + route integration (nhận list tin → route → hiện phút/vẽ đường).
- Turn-by-turn navigation (chỉ đường giọng nói/từng bước) — chỉ vẽ 1 polyline tĩnh.

---
As-built: (chưa build) — cập nhật `docs/tech_specs/Map_Routing.md` sau khi hoàn thành + verify.
