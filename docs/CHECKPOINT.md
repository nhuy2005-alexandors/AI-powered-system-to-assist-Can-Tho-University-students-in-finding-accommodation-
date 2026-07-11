# Checkpoint — Trọ CTU

_Cập nhật: 2026-07-06_

> Nguồn suy trạng thái: `task.md` (stigmergy board), git log, cấu trúc `apps/api/app/` + `apps/web/src/app/`.
> Chi tiết từng module xem `docs/tech_specs/`.

## Đã xong

- **Crawler pipeline 6 nguồn** — `apps/api/app/crawler/` (phongtro123, mogi, tromoi, bds123, nhadatcantho, nhadatcantho247). Fetcher + parser + normalize + dedup + geocode + scheduler. Sources JSON ở `apps/api/app/crawler/sources/`. Chi tiết `docs/tech_specs/Crawler_Pipeline.md` + `Crawler_Pipeline_Hardening.md`.
- **Data cleaning pipeline 5 tầng** — `apps/api/app/cleaner/pipeline.py` (`run_cleaner`): classify (phong_tro/nha/mặt bằng/khác) → validate giá → resolve area → normalize → quality_score 0..1. Search mặc định chỉ trả `listing_type=phong_tro` sạch. Chi tiết `docs/tech_specs/Data_Cleaning_Pipeline_Design.md`.
- **Auth (backend + frontend)** — backend `apps/api/app/auth/` (JWT access+refresh, OAuth provider, `router.py`). Frontend `apps/web/src/app/{login,register,me}/` + Route Handler proxy `apps/web/src/app/api/auth/`, token httpOnly cookie, middleware bảo vệ route (`apps/web/src/middleware.ts`). Chi tiết `docs/tech_specs/Frontend_Auth.md`.
- **UGC Listing CRUD** — `apps/api/app/listings/router.py` (`POST/PUT/DELETE /listings`), kiểm tra chủ sở hữu, soft-delete `status='hidden'`. Chi tiết `docs/tech_specs/UGC_Listing_CRUD.md`.
- **Frontend Listing UI** — list+lọc (`apps/web/src/app/page.tsx`), chi tiết (`listings/[id]/page.tsx`), form đăng/sửa (`listings/new`, `listings/[id]/edit`). Chi tiết `docs/tech_specs/Frontend_Listing_UI.md`.
- **Bản đồ Leaflet tương tác** — `apps/web/src/app/map/` (`MapView.tsx` dynamic ssr:false → `MapInner.tsx` react-leaflet CircleMarker + Popup OSM). Thay bản danh-sách-khoảng-cách cũ. Deps: leaflet + react-leaflet 4.x.
- **Trang "Tin của tôi"** — backend `GET /listings/mine` (`listings/router.py`, khai TRƯỚC `/{listing_id}`; repo `by_owner`), FE `apps/web/src/app/listings/mine/page.tsx` (route bảo vệ).
- **Ảnh cho form đăng tin** — `ListingForm.tsx`: textarea nhiều URL (split/trim/filter → `images[]`).
- **API core** — `apps/api/app/main.py`: health, `/health/deps` (postgres/postgis/pgvector/redis), `/crawler/status`, `/crawler/run`. Scheduler bật (`CRAWLER_ENABLED=true`, ~12 job).
- **Badge rủi ro trung thực** — `risk_level()` (`apps/api/app/listings/schemas.py:16`) trả `unknown` khi `risk_score=0` (chưa có risk engine) thay vì `safe`. FE render badge xám "Chưa rõ". Verified live: crawler listings trả `(0.0, 'unknown')`.
- **Test** — `apps/api/tests/` (test_auth, test_crawler, test_cleaner, test_listings, test_listings_crud). 86 test pass; test_listings 9/9 sau sửa badge.
- **Map & Routing — nền tảng (2026-07-06)** — spec `docs/specs/Map_Routing.md` chốt (glossary + quyết định). Cột `route_time_campus REAL[]` (`infra/db/migrations/50_route_time.sql`, đã apply, verified). ORS client `apps/api/app/listings/routing.py` (`matrix_minutes` time + `route_geometry` polyline), self-check pass + verify call thật (campus I→I = 0.0 phút → gotcha `[lng,lat]` đúng). Config `ors_api_key` (`config.py:20`). 3 campus CTU chốt (khu I/II/III, xem spec bảng Campus).
- **Route backfill (2026-07-06)** — `apps/api/app/listings/route_backfill.py`, 1 call Matrix cho 414 tin có geom. Verified DB: 414/414 có `route_time_campus`, avg khu II = 12.4 phút. **CỜ ĐỎ: 3 tin `nhadatcantho247` geocode SAI thành phố** (id 999/1003 ra Hà Nội, 1007 ra HCM) → route 122–1238 phút. Root cause = geocode trả toạ độ SAI TỰ TIN (Nominatim match tên đường ra tỉnh khác, chỉ ràng `countrycodes=vn`), KHÔNG phải bug routing.
- **Map & Routing — auto-route + API + FE (2026-07-06)** — VIỆC 4/5/6 xong, chi tiết `docs/tech_specs/Map_Routing.md`. Auto-route tin mới sau crawl (`crawler/pipeline.py` cuối `run_source`, chỉ route `route_time_campus IS NULL`) + re-route khi user sửa address (`listings/router.py` `_route_one`). `GET /listings/{id}/route?campus=0|1|2` trả polyline. `ListingOut.route_time_campus` expose ở mọi endpoint đọc. FE `map/MapInner.tsx`: campus picker + "X phút tới trường" + click→vẽ Polyline + popup hiện **address text gốc** + nhãn "vị trí tương đối" khi geocode_confidence≠high (ADR-011). Verify end-to-end: cả 2 container rebuild (`up -d --build api/web`), `ORS_API_KEY` wired qua `.env`+`docker-compose.yml`. `/route` trả polyline thật 132 điểm HTTP 200; `/listings` trả `route_time_campus`; picker+phút xác nhận trên browser (ảnh user). ADR-010 (route thật) + ADR-011 (geocode trần cấp-phường, bác Google/hand-map, budget path Goong) ghi `docs/DECISIONS.md`.
- **Geocode bbox guard (2026-07-06)** — `crawler/geocode.py` `_in_cantho()` chặn Nominatim match tên đường ra tỉnh khác (bug: 3 tin ra Hà Nội/HCM). 3 tin bẩn đã NULL hóa. GOTCHAS.md có mục ORS `[lng,lat]` + bug này.
- **Nearby limit 50→300 (2026-07-06)** — `listings/repo.py:136` `nearby()` limit cũ 50 cắt mất tin (215 visible trong 3km chỉ hiện 50). Nâng 300. Verified endpoint trả 246. GOTCHA còn: `nearby()` CHƯA áp filter sạch như search (lọc mỗi expired/hidden) → map hiện cả tin raw/nhà/mặt bằng — chưa đồng bộ với list, chờ user quyết.
- **Landmark Hồ Bún Xáng (2026-07-06)** — `crawler/geocode.py` LANDMARKS thêm `"bun xang": (10.0318, 105.7641)` xếp TRƯỚC `"dai hoc can tho"` → tin "gần ĐH Cần Thơ" có "bún xáng" snap về hồ (rìa campus, ổ trọ SV thật) thay vì tâm Trường Nông Nghiệp. Tin 991 re-geocode + re-route xong (route `[5.6,7.0,6.7]`). Đây là ngoại lệ có chủ đích của ADR-011 cho 1 hotspot; nguyên tắc "không hand-add landmark diện rộng" vẫn giữ.
- **Marker cluster (2026-07-06)** — `map/MapInner.tsx`: `CircleMarker`→`Marker`+`divIcon` (chấm xanh giữ nguyên) bọc trong `MarkerClusterGroup` (dep `react-leaflet-cluster@2.1.0`, khớp react-leaflet 4.x — bản 4.x đòi react 19, KHÔNG dùng). Lý do: geocode trần cấp-đường/phường (ADR-011) làm ~230 tin dồn lên ~12 toạ độ trùng → marker chồng khít, mắt thấy "vài chấm", 70 tin dưới 1 điểm không bấm được. Cluster hiện badge số + click bung = truy cập được từng tin, KHÔNG gộp data (mỗi tin vẫn record riêng). Verify: `/map` HTTP 200, bundle có markercluster; CHƯA verify browser (không drive được từ CLI). GOTCHA: npm báo 2 vuln (1 critical) khi cài — chưa audit, flag để check sau.

## Phân công (scope)

- **Lane Claude + user = crawler + data sạch.** Về cơ bản đã bàn giao.
- **Lane team user = 4 module AI** (Recommendation, RAG Chatbot, Roommate Matching, Risk Detection). Schema đã dựng sẵn: cột vector `embedding/preference/matching_vector`, bảng `roommate_profiles/match_requests/user_interactions`. Data đã có `quality_score` + `listing_type` để lọc tập học sạch.

## Đang làm

- **Marker cluster chờ verify browser** — `map/MapInner.tsx` đã wire xong + bundle có markercluster, nhưng CHƯA thấy tận mắt badge số + click bung (không drive browser từ CLI). User cần hard-refresh `localhost:3000/map` xác nhận.
- Working-tree changes chưa commit (`git status`) là toàn bộ công các phiên gần đây (crawler hardening, cleaner 5 tầng, FE listing, badge fix, Map & Routing, 2 fix dưới) — chưa commit.

## Tiếp theo

- (Team) 4 module AI — xem phần Phân công.
- (Nợ, làm trước deploy public) Nâng `next` 14→16 để hết sạch vuln. HIỆN dừng ở `14.2.35` (còn 1 high + 1 moderate, đều DoS/cache-poison/SSRF/smuggling — chỉ dính khi app deploy public hứng traffic; app đang local nên bề mặt ~0). KHÔNG `npm audit fix --force` lúc này: nhảy 2 major (14→16) breaking App Router + middleware auth, rủi ro > lợi khi chưa deploy. Nâng khi lên prod, có thời gian test.

## Đã đóng (phiên 2026-07-08)

- **Filter sạch cho `nearby()` (map = list)** — `listings/repo.py:144` thêm clause `(source='user' OR (cleaning_status='cleaned' AND listing_type='phong_tro'))` khớp `search()`. Trước: map hiện cả nhà/mặt bằng/raw. Verified: 3km quanh CTU 284→190 tin (loại 94 tin không-phải-trọ-sạch); endpoint `/listings/nearby?radius=3000` trả đúng 190 khớp DB. GOTCHA gọi API: param tên `radius` (KHÔNG phải `radius_m`), default 2000m.
- **npm vuln (SỬA THÔNG TIN SAI cũ: vuln KHÔNG từ `react-leaflet-cluster` mà từ `next`)** — bump `next` 14.2.18→14.2.35 (cùng major, không breaking): critical→high. Web verify sau bump: home/map/login đều HTTP 200. Còn nợ nâng next 16 (xem Tiếp theo).

## Gotcha đã dính

- ~14 tin `nhadatcantho247` thiếu district (address nguồn quá ngắn — giới hạn nguồn, không fix được phía mình).
- Classifier `khac`: đã xác minh **0 tin phòng trọ thật lọt `khac`** — bucket toàn nhà riêng/homestay/chung cư/mặt bằng (đúng cần loại). KHÔNG phải bug, không sửa.
- Cần chạy `run_cleaner` cả khi trigger crawler thủ công (`/crawler/run`) để data không kẹt ở trạng thái `raw` — đã xử lý trong `main.py`.

Xem thêm: `DECISIONS.md` (quyết định kiến trúc + lý do), `GOTCHAS.md` (bẫy kỹ thuật tích lũy).
