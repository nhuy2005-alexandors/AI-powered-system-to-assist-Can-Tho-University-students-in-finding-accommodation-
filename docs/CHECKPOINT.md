# Checkpoint — Trọ CTU

_Cập nhật: 2026-07-27_

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
- **Marker cluster (2026-07-06)** — `map/MapInner.tsx`: `CircleMarker`→`Marker`+`divIcon` (chấm xanh giữ nguyên) bọc trong `MarkerClusterGroup` (dep `react-leaflet-cluster@2.1.0`, khớp react-leaflet 4.x — bản 4.x đòi react 19, KHÔNG dùng). Lý do: geocode trần cấp-đường/phường (ADR-011) làm ~230 tin dồn lên ~12 toạ độ trùng → marker chồng khít, mắt thấy "vài chấm", 70 tin dưới 1 điểm không bấm được. Cluster hiện badge số + click bung = truy cập được từng tin, KHÔNG gộp data (mỗi tin vẫn record riêng).
- **E2E verify `/map` (2026-07-11)** — `apps/web/e2e/map.spec.ts` + `playwright.config.ts` (dep đổi `playwright`→`@playwright/test@1.61.1`, script `test:e2e`). Test assert 3 thứ phiên trước không drive được từ CLI: campus picker (Khu II active `bg-emerald-600`), badge `.marker-cluster` render, popup có "phút tới trường". PASS. Screenshot xác nhận bằng mắt: badge số "2"/"6" + chấm xanh + picker. GOTCHA: chấm marker nằm dưới div campus-picker → Playwright `click()` bị "intercepts pointer events"; phải `dispatchEvent('click')` (fire thẳng lên element leaflet bind handler, bỏ hit-test). Config không dùng `webServer` — web+api chạy sẵn trong docker, baseURL `localhost:3000` (override qua `E2E_BASE_URL`). `test-results/` đã gitignore.

- **Geocode street-level (tầng 1b) + backfill (2026-07-14)** — Trước: 122/150 tin medium/low có tên đường bị `ward_district_city()` vứt đường → snap tâm phường/quận (lệch tới 5km). Thêm tầng 1b `street_district_city()` (`apps/api/app/crawler/geocode.py:155`) trích `tên đường + Phường + Quận + Cần Thơ` → Nominatim pin đúng đường; type-guard `_STREET_TYPES` (`geocode.py:149`): match `type=đường` → high, POI in-bbox → medium (không dám high). GIỮ Phường trong query (bỏ đi thì đường dài kiểu Nguyễn Văn Cừ ~8km collapse 1 điểm sai 4km — bug đã bắt lúc test). Tầng 1 (số nhà) KHÔNG đụng → 251 high cũ nguyên. Backfill (module 1-lần, đã xoá sau khi chạy) re-geocode 162 tin (chỉ ghi khi rank ≥ cũ, 0 downgrade): 25 lên high, 137 dịch đúng vị trí. Re-route 468/468 qua ORS (chạy TRONG container `nckh-api-1` để thấy `ORS_API_KEY`). Verified: tập map low 43→28, high 110→118, 70 tin dịch >300m, 0 route vô lý (>120phút); map ảnh xác nhận pin rải theo trục đường thật (Nguyễn Văn Cừ/3 Tháng 2/Trần Hưng Đạo) thay vì dồn tâm phường. `test_crawler` 24/24 pass.

- **Geocode: reuse + city-fallback (2026-07-14; test verify 2026-07-25)** — 3 sửa ở tầng code:
  1. **Skip re-geocode tin cũ** — `repo.existing_geo()` (`crawler/repo.py:96`) đọc geom+address hiện có theo `(source, source_id)`; `run_source` (`crawler/pipeline.py:117-130`) reuse toạ độ cũ khi tin đã có geom VÀ address không đổi → chỉ gọi Nominatim cho tin mới/đổi địa chỉ (trước: full sweep re-geocode hàng trăm tin đã biết toạ độ, 1req/s, dễ bị OSM chặn). Log `geocode: X gọi mới / Y bỏ qua`.
  2. **Landmark KDC dân gian** — `geocode.py` LANDMARKS +15 địa danh nguồn `nhadatcantho247` hay dùng (Hồng Loan, 91B, Nam Long, chợ 586, CTY 8, Ecopark, Metro, 3/2...) → bắt được address không có trên Nominatim.
  3. **Tầng 5 centroid TP (`geocode.py:273`)** — mọi tầng fail nhưng tin CHẮC ở CT (list_url lọc Cần Thơ) → trả `CANTHO_CENTROID` confidence `"city"` thay vì `failed`. Verified schema chấp nhận (`geocode_confidence VARCHAR(10)`, không CHECK constraint); `cleaner/pipeline.py:123` quality_score KHÔNG cộng điểm cho `"city"` (đúng ý đồ — vị trí kém tin cậy).
  - **Số đo trực tiếp DB lúc bắt đầu phiên: `geocode_confidence='failed'` = 80/548** (100% district=NULL, phần lớn `nhadatcantho247` address cụt). Khác con số "12 tin failed" ở Gotcha dòng dưới — chưa rõ do đếm khác tập (sạch vs tổng) hay state đã đổi; cần verify lại khi Docker lên.

- **Fix 3 lỗi review của tầng 5 city-fallback (2026-07-25, test PASS)** — review bắt 3 lỗi trong chính 3 sửa ở trên; đã áp + viết test đóng lại. `test_crawler` **29/29 pass** (24 cũ + 5 mới), chạy trong container tạm từ image `nckh-api:latest`.
  1. **Nhánh fallback district là CODE CHẾT** — `pipeline.py:136` guard cũ `if lat is None and n.district`. Tầng 5 luôn trả centroid TP + `conf="city"` cho address non-empty nên `lat` KHÔNG BAO GIỜ `None` → nhánh chưa từng chạy. Guard mới `if (lat is None or conf == "city") and n.district`, và chỉ nhận kết quả district khi `d_conf != "city"` (không đổi tâm-TP lấy tâm-TP). **Đây là lý do backfill bị hoãn**: chạy với code cũ thì 80 tin `failed` bị pin hết về centroid TP thay vì tâm quận.
  2. **2 landmark key bắt bừa** (`geocode.py`, `_match_table` dùng substring) — `"586"` trần khớp cả số nhà `"586/12 Nguyễn Văn Cừ"` → đổi thành `"kdc 586"` (giữ `"cho 586"`); `"metro"` trần khớp `"Metro House"`/`"Metropolitan"` → đổi thành `"sieu thi metro"` + `"mm mega"`.
  3. **Nhãn sai trên dữ liệu thật** — `pipeline.py:128` `cached.get("geocode_confidence") or "failed"` → `or "low"`. Nhánh đó chỉ chạy khi `cached["lat"] is not None`, tức dòng ĐANG có toạ độ; gán `failed` cho nó là tự dán nhãn sai.
  - Test mới (`tests/test_crawler.py` cuối file): city-fallback-never-None · 586 không false-match · metro không false-match · district thắng city-centroid · cached có toạ độ không bị gắn `failed`.

- **Fix #4: tầng 5 gần như không bao giờ chạy — catch-all `"can tho"` ở tầng 4 (2026-07-27, test 30/30 PASS)** — self-review diff bắt thêm 1 lỗi cùng lớp với 2 landmark key bắt bừa. `WARD_CENTROIDS` có key `"can tho": (10.0333, 105.7880)`, mà `_match_table` dùng **substring** → MỌI address thật đều chứa "Cần Thơ" nên tầng 4 khớp trước, trả **đúng toạ độ `CANTHO_CENTROID`** nhưng dán nhãn `"low"`. Hệ quả: tầng 5 thành code chết với address có "Cần Thơ" (chỉ chạy khi address cụt hẳn), `city` gần như không xuất hiện, và ~80 tin `failed` cũ sẽ bị gắn `low` — tự nhận là fallback cấp phường trong khi thực chất là tâm thành phố, đúng loại "nhãn lạc quan" mà ADR-011 cấm.
  - Đo trực tiếp trước khi sửa (Nominatim monkeypatch chết, chỉ còn bảng tra): `"hem 9, Can Tho"` → `(10.0333, 105.788, 'low')`, trùng khít `CANTHO_CENTROID`.
  - Sửa: xoá key `"can tho"` khỏi `WARD_CENTROIDS` (`geocode.py:56`, để lại comment giải thích tại sao KHÔNG được thêm lại). Sau sửa cùng input → `'city'`; `"Binh Thuy, Can Tho"` vẫn `'low'` (tâm quận thật), `"CTY 8, Can Tho"` vẫn `'medium'` (landmark) → không hạ cấp tầng nào khác.
  - Test đóng lại: `test_ward_centroid_has_no_city_catch_all` (`tests/test_crawler.py`). `test_crawler` **30/30 pass**.
  - Ảnh hưởng backfill: đây là lý do THỨ HAI phải chạy backfill sau khi code đã đúng — chạy bằng code cũ thì tin cụt nhận nhãn `low` sai thay vì `city`, và badge "vị trí ước lượng" trên FE sẽ không hiện (FE chỉ ẩn badge với `high`, nên `low`/`city` đều hiện — badge OK, nhưng `quality_score` thì `low` KHÔNG cộng điểm giống `city`, nên số điểm không lệch; lệch là ở nhãn hiển thị + thống kê).

## Phân công (scope)

- **Lane Claude + user = crawler + data sạch.** Về cơ bản đã bàn giao.
- **Lane team user = 4 module AI** (Recommendation, RAG Chatbot, Roommate Matching, Risk Detection). Schema đã dựng sẵn: cột vector `embedding/preference/matching_vector`, bảng `roommate_profiles/match_requests/user_interactions`. Data đã có `quality_score` + `listing_type` để lọc tập học sạch.

## Đang làm

- **Backfill geocode — CHỜ PORT, không chờ code (2026-07-25).** Code đã đúng + test 29/29 pass; chặn duy nhất là hạ tầng: stack `nckh` KHÔNG lên được vì 3 port bị stack `infra-*` (project khác) giữ — `infra-postgres-1` chiếm 5432, `infra-redis-1` chiếm 6379, `infra-pgbouncer-1` chiếm 6432. Muốn chạy: `docker compose down` stack `infra-*` trước, rồi `docker compose up -d db redis api`. Sau khi DB lên:
  1. Chạy `run_source` 1 nguồn → xem log `geocode: X gọi mới / Y bỏ qua` xác nhận reuse (Fix 1).
  2. `docker exec nckh-api-1 python -m app.crawler.backfill` re-geocode tin cũ → kiểm `failed` giảm từ 80, `city` xuất hiện (Fix 3), và tin CÓ district phải ra tâm quận chứ KHÔNG phải `CANTHO_CENTROID` (nếu vẫn ra tâm TP → fix #1 chưa ăn).
  3. Re-route tin mới có geom (`route_time_campus IS NULL`) — verify không route vô lý (>120 phút).
  4. `test_listings_crud` 7 fail hiện tại là do THIẾU DB, không phải regression — đo lại 2026-07-27: full suite `85 passed, 7 failed`, cả 7 fail đều là `psycopg.OperationalError` lúc mở connection, đều nằm trong `tests/test_listings_crud.py`. Đã chứng minh bằng cách stash toàn bộ edit rồi chạy lại trên code gốc → fail y hệt 7 cái đó. (Lần đo trước ghi 6 — cùng nguyên nhân, khác số test được collect.)

## Tiếp theo

- (Team) 4 module AI — xem phần Phân công.
- (Nợ, làm trước deploy public) Nâng `next` 14→16 để hết sạch vuln. HIỆN dừng ở `14.2.35` (còn 1 high + 1 moderate, đều DoS/cache-poison/SSRF/smuggling — chỉ dính khi app deploy public hứng traffic; app đang local nên bề mặt ~0). KHÔNG `npm audit fix --force` lúc này: nhảy 2 major (14→16) breaking App Router + middleware auth, rủi ro > lợi khi chưa deploy. Nâng khi lên prod, có thời gian test.

## Đã đóng (phiên 2026-07-08)

- **Filter sạch cho `nearby()` (map = list)** — `listings/repo.py:144` thêm clause `(source='user' OR (cleaning_status='cleaned' AND listing_type='phong_tro'))` khớp `search()`. Trước: map hiện cả nhà/mặt bằng/raw. Verified: 3km quanh CTU 284→190 tin (loại 94 tin không-phải-trọ-sạch); endpoint `/listings/nearby?radius=3000` trả đúng 190 khớp DB. GOTCHA gọi API: param tên `radius` (KHÔNG phải `radius_m`), default 2000m.
- **npm vuln (SỬA THÔNG TIN SAI cũ: vuln KHÔNG từ `react-leaflet-cluster` mà từ `next`)** — bump `next` 14.2.18→14.2.35 (cùng major, không breaking): critical→high. Web verify sau bump: home/map/login đều HTTP 200. Còn nợ nâng next 16 (xem Tiếp theo).

## Gotcha đã dính

- **12 tin failed (không lên map)** — `nhadatcantho247` district NULL + string cụt ("hẻm 9", "Kdc CTY 8", "ĐỐI DIỆN BV NH"). Tầng 1b không cứu được vì KHÔNG biết quận/phường để neo đường. Đúng trần ADR-011 (string nguồn cụt), để lại. +1 tin UGC id 1258 mojibake (address hỏng `ef bf bd` trong DB — client test nhập lỗi cp1252 1 lần, KHÔNG phải bug write path; write path OK, xác minh bằng tin 1259/1260 cùng cụm có dấu đúng). Cân nhắc xoá 1258 (test rác).
- Backfill geom chạy từ HOST phải override `DATABASE_URL` host `db`→`localhost:5432` (host `db` chỉ resolve trong docker network). Re-route phải chạy TRONG container (`docker exec nckh-api-1 python -m app.listings.route_backfill`) vì `ORS_API_KEY` chỉ có trong container env, không có ở shell host.
- **Chạy pytest KHÔNG cần bật cả stack** (dùng khi port bị project khác chiếm): image `nckh-api:latest` còn sẵn nên chạy container tạm là đủ cho test không cần DB (`test_crawler`, `test_cleaner`):
  ```
  MSYS_NO_PATHCONV=1 docker run --rm -v "D:/Dev/Workspaces/NCKH/apps/api:/app" -w //app nckh-api:latest python -m pytest tests/test_crawler.py -q
  ```
  Hai chi tiết Windows/git-bash bắt buộc, thiếu là lỗi khó hiểu: `MSYS_NO_PATHCONV=1` (không có thì git-bash biến `/app` thành `C:/Program Files/Git/app` → daemon báo "working directory is invalid") và `-w //app` (hai gạch chéo chặn path rewrite).
- **Host KHÔNG chạy được pytest của project này** — không có `.venv`, Python host là 3.11.9 trần, thiếu toàn bộ dep (fastapi/sqlalchemy/psycopg). Phải qua container.
- ~14 tin `nhadatcantho247` thiếu district (address nguồn quá ngắn — giới hạn nguồn, không fix được phía mình).
- Classifier `khac`: đã xác minh **0 tin phòng trọ thật lọt `khac`** — bucket toàn nhà riêng/homestay/chung cư/mặt bằng (đúng cần loại). KHÔNG phải bug, không sửa.
- Cần chạy `run_cleaner` cả khi trigger crawler thủ công (`/crawler/run`) để data không kẹt ở trạng thái `raw` — đã xử lý trong `main.py`.

Xem thêm: `DECISIONS.md` (quyết định kiến trúc + lý do), `GOTCHAS.md` (bẫy kỹ thuật tích lũy).
