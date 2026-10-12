# Open mobility — bản hiện tại

## Phạm vi bàn giao

Lane map dùng Leaflet và OpenStreetMap-compatible adapters. Kế thừa cluster, pin/popup, chọn tin từ danh sách hoặc map, Enter, fly-to, resize, tìm kiếm tiếng Việt không dấu, sắp xếp giá NULL cuối và sidebar responsive. API/client giữ catalog789 và các trường UNKNOWN/NULL; ảnh là URL.

P4 lịch sử đã nghiệm thu ngày 2026-10-07. Ngày 2026-10-11 đã chạy lại real acceptance và receipt verifier trên clone789, cả hai PASS sau sửa startup/cache/pilot. Kết quả gate/provider hiện hành xem `docs/CHECKPOINT.md` và artifact private khớp source; không lấy PASS lịch sử làm chứng nhận tree mới. FullAPI1471passed/47skipped/7known crawler-safe-backfill failures là mốc lịch sử, không phải full-repository green hiện tại. Không dùng số test synthetic làm độ phủ dữ liệu thật.

## P4 nghiệm thu dữ liệu thật (2026-10-07)

- Clone giữ nguyên trong Docker project `nckh-mobility-acceptance`: container `nckh-mobility-acceptance-db`, volume `nckh_mobility_acceptance_pgdata`, database `mobility_catalog_acceptance`, loopback `127.0.0.1:5455`, image `sha256:dcea513d8f8c0bd2b314bfaa672d1bb3a91d100c401afe34f139dcd3c5869bdd`.
- Catalog/API/UI đều khớp 789 ID duy nhất; có 8 trang HTTP/API và 2 tin không có tọa độ. AC1–AC6 đều true; browser không thử request ngoài origin (`external_attempts=0`).
- Kết nối nghiệm thu dùng role `mobility_catalog_reader`: transaction read-only bật, DML bị từ chối. Digest mọi bảng public và view catalog trước/sau giống nhau. Không sửa nội dung catalog trong DB.
- Receipt và ảnh chụp nằm trong runtime riêng có ACL owner-only, ngoài repository: [REAL_ACCEPTANCE.json](D:/Dev/Data/NCKH/mobility-catalog-acceptance-20261004-01/REAL_ACCEPTANCE.json). File mật khẩu trong cùng thư mục không được đưa vào repo hoặc chia sẻ qua chat.
- API/UI test server chỉ chạy trong lúc harness nghiệm thu và đã tự dừng; container PostgreSQL và volume được giữ nguyên để kiểm tra/sử dụng nội bộ. Không chạy `down -v`, không xóa volume.

## API và dữ liệu

- Backend: `/mobility/campuses`, `/mobility/listings`, `/mobility/routes`, `/mobility/nearby`.
- Frontend cùng origin: `/api/mobility/*`; trang `/map`.
- Ba campus: `khu_i`, `khu_ii`, `khu_iii`; các tọa độ đang PROVISIONAL, chưa xác nhận cổng vào.
- Tuyến có chiều `LISTING_TO_CAMPUS`. Thiếu vị trí trả LOCATION_UNAVAILABLE và không có số đo tuyến.
- ORS hỗ trợ WALK/BICYCLE. MOTORBIKE/BUS trả UNSUPPORTED_MODE; BUS vẫn cần departure_time có UTC offset hợp lệ. Không thay phương tiện bằng ô tô.
- Không cấu hình trả NOT_CONFIGURED, số đo và polyline NULL, evidence NONE.
- Cảnh báo dựa trên chất lượng/vị trí dữ liệu. Không có điểm an ninh hoặc mô hình ML đã được hiệu chỉnh.

## Cấu hình

`MOBILITY_ENABLED` bật lane. `MOBILITY_DATABASE_URL` chỉ trỏ DB catalog theo hợp đồng lane; không dùng DSN production để thử. `API_INTERNAL_URL` nối frontend với API.

Provider mặc định disabled: `MOBILITY_ROUTING_PROVIDER`, `MOBILITY_PLACES_PROVIDER`, `MOBILITY_GEOCODER_PROVIDER`. ORS/Overpass/Nominatim có adapter và policy gate chung; provider cần endpoint, policy/hash được duyệt và budget trước khi gửi request. Key chỉ server, không đưa vào UI hay gói bàn giao.

Tiles cần đầy đủ `MOBILITY_TILES_ENABLED`, `MOBILITY_TILE_URL`, `MOBILITY_ALLOWED_TILE_ORIGIN`, `MOBILITY_TILE_ATTRIBUTION`. Khi chưa chọn host và duyệt chính sách, tiles tắt; nền Leaflet không phải bản đồ đường phố live đã nghiệm thu. Google adapter lịch sử không được registry chọn cho production.

POI chỉ là quan sát có độ phủ PARTIAL. Có công an gần trọ không chứng minh khu vực an toàn. Khoảng cách POI là đường thẳng; route chỉ có độ dài/thời gian đo khi provider trả kết quả có nguồn gốc hợp lệ.

## Chạy và kiểm tra

Backend dependencies: `apps/api/requirements.txt`; frontend: `apps/web/package-lock.json`. Không xuất `.env`, key hay auth files.

```powershell
# Từ apps/web, với API_INTERNAL_URL và MOBILITY_ENABLED cấu hình riêng
node node_modules/next/dist/bin/next build
node node_modules/next/dist/bin/next start -p 3000
```

Offline instrument và bằng chứng nằm trong `.superpowers/sdd/2026-10-05-open-mobility-agent-plan/`: P1 guard/v2receipt proof, P3 RED/GREEN, independent review và proposed offline gate. Receipt framework hiện hành phải khớp gate/candidate; lịch sử PASS không thay thế kiểm tra hiện tại.

P4 runbook: `docs/specs/mobility-catalog-live-acceptance.md` và `docs/specs/open-mobility-migration.md`. P4 clone riêng5455 đã được nghiệm thu và giữ lại; DB5432 và handoff5454 không bị chạm. Nếu chạy nghiệm thu lại, dùng đúng runtime/receipt/code pins và xác minh trạng thái target trước; không chạy bootstrap mới trên runtime đang tồn tại. Không phát hành công khai dữ liệu nguồn từ gói INTERNAL.

## P5 demo tương tác có giới hạn

Policy đã duyệt ở `docs/planning/open-mobility-provider-policy.md`. Launcher `scripts/open_mobility_pilot.py` chỉ mở app mobility riêng: API8033, UI3033, một worker, role clone read-only. Key ORS đọc từ cấu hình backend hiện có hoặc nhập ẩn; frontend không nhận key/DSN. Không import production main hoặc crawler.

`manifest` chạy production build mới trong closed environment, pin 83 source files và compiled BUILD_ID/server/static/JSON; số lượng là mốc build 2026-10-11, command phải đo lại khi source thay đổi. Operator đối chiếu digest của manifest riêng trước `run`; runner kiểm matching P4 receipt/clone và pin trước outbound, sau browser và trước PASS.

```powershell
& 'D:/Dev/SDKs/Python/python.exe' scripts/open_mobility_pilot.py manifest
# Thay hai placeholder bằng path/digest vừa trả về, không dùng manifest cũ.
& 'D:/Dev/SDKs/Python/python.exe' scripts/open_mobility_pilot.py run --manifest '<private-manifest-path>' --manifest-sha256 '<digest>'
```

Mỗi lượt: một WALK + một BICYCLE tới khu II, một pharmacy/1000m, một public landmark geocode và một lần lặp cache. Tiles visible single-view, tối đa60 outbound attempts, send-start cách >=1s, deadline90s, zero retry/redirect; cache tile owner-only tối đa128 file theo TTL provider. Không tăng budget hoặc rotate host khi fail.

Startup fit đồng bộ theo catalog/campus trước khi attach tiles; không tải default-zoom batch. Teardown giữ interceptor, đóng admission rồi drain toàn handler có timeout; không gỡ guard bằng unrouteAll. Pending/deadline/budget/transport/cache/fulfill/lifecycle failures hạ NOT_VERIFIED; snapshot counters detached. Browser close phụ thuộc timeout Playwright; launcher Windows-only dùng pywin32==312 Job Object, tạo suspended/assign trước ResumeThread, terminate cả cây và đợi ActiveProcesses=0 tối đa5s khi normal exit/timeout110s. Nếu containment/dependency không khả dụng thì fail-closed, không fallback process rời. Native child/grandchild timeout và parent-exit canary là kiểm chứng dọn process, không phải provider evidence. Receipt lỗi đã khử nội dung; không ghi được file thì stdout REPORT_WRITE_FAILED. Deadline tile dùng wall clock, chưa kiểm clock rollback. Không suy hoàn hảo từ một pilot.

Nominatim cache chung trong RAM:128 entry/24h, giữ timestamp quan sát, cache hit zero outbound; demo-only POST `/mobility/geocode`, không autocomplete/batch. Chưa có frontend geocoding search. Có thể tắt từng capability; không giả route/POI hoặc thay MOTORBIKE/BUS bằng mode khác. Campus/các vị trí catalog còn gần đúng, chưa xác nhận cổng; POI PARTIAL không phải điểm an ninh. Public release và coverage toàn789 chưa được chứng nhận. Launcher dừng riêng process nó mở, giữ nguyên mọi DB/volume.
