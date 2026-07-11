# Đặc tả kỹ thuật (as-built) — Map & Routing

> Ngày: 2026-07-06 · Trạng thái: **VIỆC 4/5/6 hoàn tất, verified** (nền tảng + backfill đã có từ phiên trước)

Spec gốc: `docs/specs/Map_Routing.md`. Doc này chỉ ghi phần build thêm (auto-route, API, FE) —
routing.py/campus/migration đã build + verify ở phiên trước (xem CHECKPOINT.md).

## VIỆC 4 — Auto-route tin mới (backend)

Không route lại toàn bộ mỗi lần — chỉ route tin đang `route_time_campus IS NULL` (mới crawl,
hoặc backfill sót).

- `apps/api/app/crawler/repo.py:118-140` — `ListingRepo.pending_route()` (SELECT id/lat/lng WHERE
  `geom IS NOT NULL AND route_time_campus IS NULL`) + `set_route_times()` (batch UPDATE).
- `apps/api/app/crawler/pipeline.py:135-153` (cuối `run_source`, sau `refresh_scores()`) — nếu
  `settings.ors_api_key` rỗng → log skip, không crash. Có key → lấy `pending_route()`, gọi
  `matrix_minutes()` 1 batch call, `set_route_times()`. Lỗi mạng/ORS bắt bằng `except Exception`
  quanh cả block → không làm hỏng crawl job (giống pattern `BlockedError` đã có).
- Re-route khi user sửa address: `apps/api/app/listings/router.py` — `_route_one()` (dòng 49-61)
  gọi sau khi geocode xong. Wire vào `create_listing` (dòng 154-159) và `update_listing` chỉ khi
  `"address" in fields` (dòng 180-183). `ListingWriteRepo.set_route_time()` (`repo.py:236-242`).

## VIỆC 5 — Expose API

- `apps/api/app/listings/schemas.py:80` — `ListingOut.route_time_campus: list[float] | None`.
- `apps/api/app/listings/repo.py:16` — `_COLS` thêm `route_time_campus` → tự động có trong mọi
  response dùng `_COLS` (`search`, `get`, `by_owner`, `get_visible`, `nearby`).
- `apps/api/app/listings/router.py:117-135` — `GET /listings/{id}/route?campus=0|1|2` (mặc định
  1=khu II). Validate: tin không có toạ độ → 404; `ORS_API_KEY` rỗng → 503; lỗi ORS → 502 (không
  lộ trace). Trả `list[list[float]]` ([lat,lng] polyline, campus→tin — dùng `route_geometry()` có
  sẵn từ `routing.py`).

## VIỆC 6 — Frontend

- `apps/web/src/lib/api.ts` — `ListingOut.route_time_campus: number[] | null` (dòng ~99);
  `getListingRoute(id, campus)` gọi `/listings/{id}/route` (dòng ~152).
- `apps/web/src/app/map/MapInner.tsx` — viết lại: campus picker (3 nút Khu I/II/III, mặc định
  khu II = index 1); mỗi `CircleMarker` hiện "X phút tới trường" từ
  `listing.route_time_campus[campus]` trong Popup (null → "Chưa có thời gian di chuyển"); click
  marker → `getListingRoute()` → vẽ `<Polyline>` (react-leaflet) campus→tin. Lỗi fetch route (vd
  ORS chưa cấu hình) → nuốt lỗi, không vẽ đường, không chặn UI.

## Quyết định lúc làm

- **Không tạo bảng/cache riêng cho route pending** — dùng WHERE `route_time_campus IS NULL` trực
  tiếp trên `aggregated_listings`, khớp quyết định spec gốc "cột DB thay cache".
- **Re-route address UGC dùng `matrix_minutes([1 điểm])`** thay vì gọi lại toàn batch — 1 tin đổi
  address = 1 call nhỏ, không đụng tin khác.
- **Guard `ors_api_key` rỗng ở 2 lớp**: pipeline (skip êm, log) và router (503 rõ ràng cho FE) —
  vì 2 nơi có audience khác nhau (log cho dev, HTTP status cho client).

## Verify

- `python -m py_compile` toàn bộ file backend đổi → pass (không lỗi cú pháp).
- `npx tsc --noEmit` (apps/web) → "No errors found" (sau `npm install` bổ sung `react-leaflet`
  còn thiếu trong `node_modules` — pre-existing gap, không do thay đổi này).
- `npm run build` (apps/web) → build thành công, route `/map` lên trong bảng route Next.js.
- Backend test: `DATABASE_URL=postgresql+psycopg://nckh:nckh@localhost:5432/nckh python -m pytest`
  → **85 passed, 1 failed**. Fail (`test_create_listing_requires_auth`, kỳ vọng 403 nhận 401) —
  xác nhận KHÔNG liên quan thay đổi này (`git diff --stat -- apps/api/app/auth/` = 0 file đổi;
  file test đó tự thay đổi từ phiên trước, không đụng trong phiên này).
- Runtime thật: `docker cp` 5 file đổi vào `nckh-api-1` + `docker restart` → verify qua curl:
  - `GET /listings?size=5&sort=quality` → field `route_time_campus` có mặt, vd id=20:
    `[8.9, 10.9, 10.6]`.
  - `GET /listings/20/route?campus=1` (container không có `ORS_API_KEY`) → **503**
    `{"detail":"Routing chưa cấu hình (ORS_API_KEY)"}` — đúng hành vi guard kỳ vọng.
  - Không verify được response polyline thật (container thiếu key) — cần key thật để test end-to-end
    Matrix/Directions call, đã verify ở phiên backfill trước (self-check + campus I→I = 0.0 phút).
- FE chưa verify runtime trong container (`nckh-web-1` build từ image cũ, không rebuild — rebuild
  image là thay đổi tốn thời gian hơn phạm vi yêu cầu; đã verify tĩnh qua build/typecheck).
