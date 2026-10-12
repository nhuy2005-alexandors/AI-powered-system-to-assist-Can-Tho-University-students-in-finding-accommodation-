# Bàn giao lane map / mobility — 2026-10-12

## Phạm vi và nhánh

Nhánh: `codex/open-mobility-handoff`. Base: `59a039518175eae12d1158365e74124d9a7451ce`.
Đây là bản tách riêng từ cây làm việc có nhiều lane, không phải toàn bộ cây dirty.
Không kèm crawler/contact/vault/PII/export, credentials, dữ liệu thô, volume hay receipt riêng tư.
Không merge vào `main` tự động. Nhóm trưởng chịu trách nhiệm tích hợp và chạy lại trên nhánh hợp nhất.

## Hợp đồng cần giữ

- `/map` dùng catalog mobility khi `MOBILITY_ENABLED=true`; không âm thầm fallback sang tập legacy đã lọc.
- Backend: `GET /mobility/campuses`, `GET /mobility/listings`, `POST /mobility/routes`, `POST /mobility/nearby`. `POST /mobility/geocode` chỉ được đăng ký bởi app pilot riêng qua `demo_geocode_enabled=True`; `main.py` thường không đăng ký nó. Web proxy ở `/api/mobility/*` không chứa provider key.
- Catalog độc lập chỉ đọc `public.catalog_handoff_v1`, kiểm đúng 789 hàng và package/hash cố định trong `catalog_repo.py`. Cần bàn giao Docker/catalog riêng; repository không dựng view hay nạp dữ liệu này.
- Routing theo chiều tin trọ → campus. WALK/BICYCLE được hỗ trợ; MOTORBIKE/BUS trả unsupported, không thay xe máy bằng ô tô.
- Diện tích thiếu giữ NULL. Vị trí thiếu vẫn ở danh sách, không tạo pin giả. Tọa độ và cổng campus chưa được xác minh tại thực địa.
- POI thiếu không có nghĩa khu vực không có tiện ích. Coverage PARTIAL; cảnh báo chất lượng/vị trí không phải điểm an ninh hay mô hình ML được hiệu chuẩn.
- Google adapter chỉ là nền móng/fixture lịch sử; registry hiện chọn open providers. Không bật Google để chữa lỗi lane này.

## Tích hợp cho agent nhóm trưởng

Làm trong checkout sạch của nhánh tích hợp, không reset/stash cây người khác.

```powershell
git fetch origin
git switch <nhanh-tich-hop>
git diff --stat 59a039518175eae12d1158365e74124d9a7451ce origin/codex/open-mobility-handoff
git merge --no-ff --no-commit origin/codex/open-mobility-handoff
# Giải quyết conflict, chạy các kiểm tra bên dưới, rồi mới commit merge.
```

Chỗ dễ conflict: `apps/api/app/main.py`, `config.py`, `listings/*`, `apps/web/src/app/map/*`, `src/lib/api.ts`, `config.ts`, package lock và `tests/conftest.py`.
Giữ wiring auth/contact của lane khác khi ghép `main.py`; chỉ thêm mobility engine/router, không thay engine production.
Giữ map UI đã tái dùng: cluster, popup, chọn tin, map–list, resize, tìm kiếm/sắp xếp; không nhận lại map page cũ làm mất feature flag và NULL/race guards.
Conftest chặn mạng/DB mặc định. Validator UGC là dependency tùy chọn của lane khác: nếu chưa có thì DB-opt-in fail closed; không bỏ guard để làm suite xanh.

## Cấu hình không có bí mật

Backend đọc biến môi trường (hoặc `.env` riêng, không commit):

```ini
MOBILITY_ENABLED=true
MOBILITY_DATABASE_URL=postgresql+psycopg://<read-only-role>:<password>@<catalog-host>:<catalog-port>/<catalog-db>
MOBILITY_LIVE_ENABLED=false
GOOGLE_MAPS_ENABLED=false
GOOGLE_LIVE_ENABLED=false
```

Để demo live, đặt `MOBILITY_LIVE_ENABLED=true` và `MOBILITY_ORS_API_KEY` chỉ ở backend.
`main.py` dùng `build_demo_live_settings`: endpoint/policy/hash được code-bound; quota 30 request/provider/process, tối đa 1 request/giây, 1 concurrent, hết hạn 2026-12-31.
Chạy đúng một backend worker; không tăng workers để lách giới hạn. Nominatim chỉ truy vấn tương tác địa danh công cộng, cache memory 24h, không batch/autocomplete.
Không dùng quota demo như cấu hình production. Không tự refresh catalog hay crawl nguồn khi khởi động.

Web dùng `API_INTERNAL_URL` trỏ API và `MOBILITY_ENABLED=true`.
Muốn nền bản đồ, thêm `MOBILITY_TILES_ENABLED=true`, `MOBILITY_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png`, `MOBILITY_ALLOWED_TILE_ORIGIN=https://tile.openstreetmap.org`, `MOBILITY_TILE_ATTRIBUTION=© OpenStreetMap contributors`.
Không bật tile prefetch/download; tuân thủ attribution/cache policy. Thiếu cấu hình tile thì UI local-only vẫn giữ danh sách.

## Kiểm tra trên checkout tích hợp

Python >=3.11, Node phù hợp Next14, cài dependencies từ manifest. Windows live pilot cần pywin32.

```powershell
python -m pip install -r apps/api/requirements.txt
$env:MOBILITY_ENABLED='false'
$env:MOBILITY_LIVE_ENABLED='false'
$env:GOOGLE_MAPS_ENABLED='false'
$env:GOOGLE_LIVE_ENABLED='false'
python -m pytest apps/api/tests/test_mobility_api.py apps/api/tests/test_mobility_catalog.py apps/api/tests/test_mobility_contracts.py apps/api/tests/test_mobility_geocoder.py apps/api/tests/test_mobility_ors.py apps/api/tests/test_mobility_overpass.py apps/api/tests/test_mobility_places.py apps/api/tests/test_mobility_provider_policy.py apps/api/tests/test_mobility_routes.py apps/api/tests/test_mobility_runtime_policy.py apps/api/tests/test_mobility_warnings.py apps/api/tests/test_routing_legacy_contract.py apps/api/tests/test_mobility_catalog_acceptance_guard.py apps/api/tests/test_open_mobility_pilot_guard.py apps/api/tests/test_open_mobility_tile_pilot_guard.py -q
cd apps/web
npm ci
npx playwright install chromium
npx playwright test --config=playwright.mobility.config.ts
npm run build
```

Chạy test offline từ môi trường không chứa provider key/live flags và không đọc `.env` có bí mật.
Không suy ra toàn repo green từ suite lane này; các test DB/crawler khác cần điều kiện riêng.
`docs/.codex-gate.json` là gate offline cho bản tách, dùng `python` và `node` trong PATH.
Hai gate catalog JSON và catalog/pilot scripts giữ nguyên pin/đường dẫn lịch sử của máy tác giả: Python `D:/Dev/SDKs/Python`, dữ liệu/runtime `D:/Dev/Data/NCKH/...`.
Chúng KHÔNG phải portable CI gate. Không sửa pin chỉ để xanh; nếu cần nghiệm thu mới trên máy khác, sửa thiết kế/harness có review và tạo receipt mới.

## Bằng chứng và giới hạn

Historical accepted trên cây nguồn trước khi tách: P4 đọc đủ 789 tin qua DB/API/UI, DML bị chặn, digest không đổi; P5 `P5_LIVE_20261012T062742Z.json` xác nhận API/UI WALK 2944.7m/2120.1s, BICYCLE 2904m/629.3s, pharmacy1000m 15 POI/PARTIAL, backend geocode và cache hit, 20/20 tile tải thành công.
SHA256 receipt P5: `b4dc52038524798cbc055ce8cd974ba8b310d13c1b7d8adee91ebd323a897906`.
Receipt/runtime/screenshot ở gói evidence riêng, không Git. Kết quả đó không chứng nhận bản merge mới, toàn bộ789 tuyến, geocoding UI, MOTORBIKE/BUS, hay quyền phát hành dữ liệu công khai.
Bản Git tách phải có kiểm tra offline/build/browser riêng ở mục release evidence dưới đây. Live của bản tách/merge chưa chạy lại.
Catalog và ảnh URL dùng INTERNAL; gửi Docker789 qua kênh bàn giao riêng, không commit dataset.

## Release evidence

Ứng viên tách tại worktree sạch đã được root trực tiếp kiểm tra ngày 2026-10-12:

- Python mobility/pilot/legacy contract: `492 passed`, `0 failed`, `0 skipped`; một cảnh báo deprecation Starlette/httpx hiện hữu.
- Browser Playwright mobility: `38 passed`, `0 failed` trong 60.37 giây; providers live và tiles tắt.
- `npm ci --no-audit --no-fund`: cài đúng lockfile, exit 0.
- Next production build: compile, lint/type check, 14/14 static pages và route `/map` thành công, exit 0.
- Secret signature scan trên toàn bộ staged paths: 0 match; `git diff --cached --check` sẽ được chạy lại trên exact release candidate.
- Chưa chạy lại provider live hoặc catalog Docker cho commit tách. Đây là `OFFLINE CANDIDATE`, không phải production/live certification.
- Release remediation: pilot chỉ dùng `MOBILITY_ORS_API_KEY`; hai ca chỉ có legacy `ORS_API_KEY` từ env/file đã fail trước sửa, toàn pilot suite 22 passed sau sửa. Nhập key tương tác ẩn vẫn được hỗ trợ.
