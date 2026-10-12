# Bàn giao dịch vụ map / mobility

Ngày: 2026-10-12. Nhánh: `codex/open-mobility-handoff`.
Đối chiếu với `apps/api/app/mobility/providers/demo_policy.py`, `open_config.py`, `main.py` và `apps/web/src/lib/config.ts`.

## Dịch vụ và URL đang dùng

| Chức năng | Dịch vụ | Endpoint mà code gọi | Key |
| --- | --- | --- | --- |
| Đi bộ | ORS / HeiGIT | POST `https://api.heigit.org/openrouteservice/v2/directions/foot-walking/geojson` | Backend `MOBILITY_ORS_API_KEY` |
| Xe đạp | ORS / HeiGIT | POST `https://api.heigit.org/openrouteservice/v2/directions/cycling-regular/geojson` | Cùng key ORS |
| Tiện ích quanh trọ | Overpass | POST `https://overpass-api.de/api/interpreter` | Không cần key |
| Geocoding địa danh | Nominatim | GET `https://nominatim.openstreetmap.org/search` | Không cần key |
| Nền bản đồ | OSM raster tiles | GET `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | Không cần key |

Các URL trên là cấu hình của bản code bàn giao; không phải cam kết uptime của dịch vụ.
Google Maps không được chọn trong runtime hiện tại. Key Google cũ không nằm trong gói service này.
ORS WALK/BICYCLE gửi tọa độ tin → campus; MOTORBIKE/BUS chưa được hỗ trợ.
`MOBILITY_ORS_BASE_URL` dùng origin `https://api.heigit.org`, adapter thêm path `/openrouteservice/v2/...`.

## Gói key riêng

Key thật đã được xuất từ cấu hình hiện có vào gói **ngoài repository**:
`D:/Dev/Data/NCKH/mobility-service-handoff-20261012/`.

- `backend.mobility.env`: có key ORS thật dưới đúng biến `MOBILITY_ORS_API_KEY`, URL và cờ của backend.
- `web.mobility.env`: URL API nội bộ, cấu hình tile và attribution; không có key ORS.
- `README.md`: cách nạp file và giới hạn đã kiểm chứng.
- `compose.mobility.private.yaml`: override Docker không chứa key, nạp hai env file và DSN catalog từ biến môi trường.
- `MOBILITY-SERVICES-PRIVATE.zip`: gói gửi riêng gồm đúng bốn file trên, đã kiểm tra inventory.

Chủ máy gửi `backend.mobility.env` cho nhóm trưởng qua kênh riêng. Không dán vào PR, issue, log hoặc chat công khai.
Đây là một lần chuyển key có chủ đích từ cấu hình `ORS_API_KEY` cũ sang biến mobility; runtime/pilot không tự fallback sang biến cũ.
Tệp được xuất cục bộ không đồng nghĩa đã được gửi đến máy của thành viên khác.
Gói không có mật khẩu DB, JWT, tài khoản Google hay credentials production.

## Backend

Mẫu cấu hình (key thật chỉ nằm trong file riêng):

```ini
MOBILITY_ENABLED=true
MOBILITY_LIVE_ENABLED=true
MOBILITY_ORS_API_KEY=<from-private-backend-file>
MOBILITY_ROUTING_PROVIDER=ors
MOBILITY_PLACES_PROVIDER=osm_overpass
MOBILITY_GEOCODER_PROVIDER=nominatim
MOBILITY_ORS_BASE_URL=https://api.heigit.org
MOBILITY_OVERPASS_URL=https://overpass-api.de/api/interpreter
MOBILITY_NOMINATIM_URL=https://nominatim.openstreetmap.org
GOOGLE_MAPS_ENABLED=false
GOOGLE_LIVE_ENABLED=false
CRAWLER_ENABLED=false
```

Khởi động từ repo root để đường dẫn file và import ổn định. Máy nhận thay `<private-backend-env-path>` bằng đường dẫn tuyệt đối tới file đã giải nén; đường dẫn `D:/Dev/Data/...` ở trên chỉ thuộc máy xuất gói:

```powershell
python -m uvicorn app.main:app --app-dir apps/api --env-file <private-backend-env-path> --host 127.0.0.1 --port 8000 --workers 1
```

Backend còn cần cấu hình ứng dụng của nhánh tích hợp: `DATABASE_URL`, `REDIS_URL`, JWT và DSN catalog chỉ đọc `MOBILITY_DATABASE_URL`.
`DATABASE_URL` phục vụ listings/auth của ứng dụng; phải trỏ DB tích hợp được nhóm duyệt. Catalog789 dùng DSN độc lập `MOBILITY_DATABASE_URL` với role chỉ đọc.
Nạp các biến đó bằng môi trường/private config của nhóm. File service không có các giá trị này và không thay credentials hiện hữu.
`--env-file` bổ sung biến vào process; biến môi trường đã tồn tại có ưu tiên cao hơn. Dừng và khởi động lại backend sau khi thay key.
`main.py` dựng policy demo từ code khi bật live; các biến URL/provider không tự cấp policy mới hay cho phép đổi host.

## Web

File riêng `web.mobility.env` chứa:

```ini
API_INTERNAL_URL=http://127.0.0.1:8000
MOBILITY_ENABLED=true
MOBILITY_LIVE_ENABLED=false
GOOGLE_MAPS_ENABLED=false
GOOGLE_LIVE_ENABLED=false
MOBILITY_TILES_ENABLED=true
MOBILITY_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
MOBILITY_ALLOWED_TILE_ORIGIN=https://tile.openstreetmap.org
MOBILITY_TILE_ATTRIBUTION=© OpenStreetMap contributors
```

Đưa các biến vào môi trường web hoặc ghép vào `apps/web/.env.local` riêng của nhóm trước khi chạy Next.
Không ghi đè một `.env.local` có sẵn; chỉ bổ sung các biến mobility.
Chạy từ `apps/web`: `npm ci`, `npm run build`, `npm run start`; truy cập `http://localhost:3000/map`.
Không đặt ORS key trong `NEXT_PUBLIC_*`, browser hay file env web.

## Docker của nhánh tích hợp

Compose hiện tại không truyền `MOBILITY_*` vào service `api` và mặc định `CRAWLER_ENABLED=true`. Cần thêm override riêng như sau; file override không chứa key và không thay DB/Redis của stack:

```yaml
services:
  api:
    env_file:
      - ${MOBILITY_BACKEND_ENV_FILE:?Set absolute path to backend.mobility.env}
    environment:
      MOBILITY_ENABLED: "true"
      MOBILITY_LIVE_ENABLED: "true"
      MOBILITY_DATABASE_URL: ${MOBILITY_DATABASE_URL:?Set separate read-only catalog DSN}
      CRAWLER_ENABLED: "false"
      GOOGLE_MAPS_ENABLED: "false"
      GOOGLE_LIVE_ENABLED: "false"
  web:
    env_file:
      - ${MOBILITY_WEB_ENV_FILE:?Set absolute path to web.mobility.env}
    environment:
      API_INTERNAL_URL: http://api:8000
      MOBILITY_ENABLED: "true"
```

Nhóm trưởng lưu đoạn trên thành `compose.mobility.private.yaml` ngoài Git, rồi đặt `MOBILITY_BACKEND_ENV_FILE`, `MOBILITY_WEB_ENV_FILE` bằng đường dẫn tuyệt đối trên máy nhận.
Nạp `MOBILITY_DATABASE_URL` từ private configuration của nhóm; host trong DSN phải truy cập được từ container. `localhost` bên trong container không phải máy host; Docker Desktop có thể dùng `host.docker.internal` nếu catalog được publish trên host.
Env file nạp key, còn khối `environment` ép crawler tắt và chọn DSN catalog; khối này có ưu tiên cao hơn env file.

Trên stack tích hợp đã có DB/Redis được nhóm duyệt:

```powershell
docker compose -f docker-compose.yml -f <absolute-private-override-path> config --quiet
docker compose -f docker-compose.yml -f <absolute-private-override-path> up --build -d --no-deps api web
```

Lệnh đầu chỉ kiểm tra cấu hình. Không in `docker compose config` đầy đủ vì nó có thể hiện key đã nội suy.
Lệnh sau cập nhật `api`/`web`; chuẩn bị DB/Redis và gói catalog789 là bước riêng của nhóm trưởng.

## Hợp đồng, quota và tình trạng

- API ứng dụng: GET `/mobility/campuses`, GET `/mobility/listings`, POST `/mobility/routes`, POST `/mobility/nearby`; web dùng proxy `/api/mobility/*`.
- `POST /mobility/geocode` chỉ có ở app pilot riêng được tạo bằng `create_demo_app`; backend `app.main` và web hiện chưa expose geocoding tương tác.
- Policy demo: tối đa 30 request/provider/process, 1 request/giây, 1 concurrent; connect timeout 2s, request timeout 10s, response tối đa 1MiB; expiry 2026-12-31 UTC. Chạy 1 worker; giới hạn process không phải quota tổng của tài khoản ORS.
- Nominatim: địa danh công cộng, tương tác, cache memory 24h; không batch/autocomplete. OSM tiles: giữ attribution và cache theo policy, không prefetch/download hàng loạt.
- Gói service không khởi chạy Docker, crawl dữ liệu, gọi thử provider hay phát sinh request khi xuất file.
- P5 trên cây nguồn ngày 2026-10-12 đã có receipt API/UI LIVE cho WALK/BICYCLE/Overpass/geocode/tiles. Commit tách và máy nhận chưa được chạy live lại; việc key được xuất không chứng minh key còn hoạt động ở lúc nhận.
- Catalog789 cần view `public.catalog_handoff_v1` từ gói Docker riêng. DSN dùng role chỉ đọc; không dùng DB production để thay thế khi thiếu catalog.

Sau merge và nạp private config, agent nhóm trưởng kiểm tra status/provenance của từng response; HTTP200 đơn thuần không đủ chứng minh routing/POI thành công.
