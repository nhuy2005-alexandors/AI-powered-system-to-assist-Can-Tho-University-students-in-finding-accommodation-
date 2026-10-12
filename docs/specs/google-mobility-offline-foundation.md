# Lane bản đồ, routing và tiện ích — Google, offline-first

Ngày: 2026-10-04. Trạng thái: USER_APPROVED_FOR_OFFLINE_IMPLEMENTATION, chờ đóng fresh spec-critic trước code.
Tier hiện tại: strict. Google live/pilot chưa được mở.

## Mục tiêu đã chốt

Sinh viên chọn chỗ ở trong catalog789, chọn một trong ba campus và phương tiện xe máy/đi bộ/xe đạp/bus; xem thông tin di chuyển, tiện ích trong bán kính và cảnh báo về vị trí chưa chắc chắn. Chuẩn bị Google provider và kiểm thử offline khi chưa có key. Không chuyển sang phương án OSM phụ; không gọi Google hoặc ORS trong giai đoạn offline.

Google live = NOT RUN. Khả năng hỗ trợ từng chế độ tại Cần Thơ, giá, SKU, quota, điều khoản lưu/cache/attribution/display đều UNVERIFIED cho đến bước kiểm tra chính thức và pilot. Không dùng fixture làm bằng chứng độ phủ hoặc kết quả live.

## Nền có sẵn và khoảng trống

- `apps/web/src/app/map/MapInner.tsx`: Leaflet/OSM, clustering, polyline và nhãn vị trí tương đối.
- `apps/api/app/listings/routing.py`: ORS driving-car, Matrix trọ→campus; router hiện vẽ campus→trọ. Không gọi driving-car là xe máy.
- `apps/api/app/listings/repo.py`: search/nearby chỉ nhận user hoặc cleaned+phong_tro, nearby giới hạn300. Không dùng nguyên filter này cho catalog789.
- `apps/api/app/listings/schemas.py`: route_time_campus chưa nhận phần tửNULL; contract mới phải nhận từng campus có thể không có tuyến.
- Chưa có Google Routes/Places, POI quanh trọ hay ML routing-confidence trong source đã kiểm.
- Master plan2026-09-20 là tài liệu đề xuất lịch sử; trạng thái DB/G1 cũ trong đó không phải hiện trạng. ADR010/011 vẫn là lựa chọn legacy ORS/OSM, không bị âm thầm thay thế.

## Biên dữ liệu và triển khai

Giữ bất biến ZIP789 SHA25cbfca2a36adf2f93772a5e48db8f6a0a8b48e777de41668d7a4b4ee5911a4a, catalog SHA b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947 và schema đã bàn giao. Không đổi raw thành cleaned để vượt filter; không viết lại diện tích/rating/tọa độ. Không đụng DB gốc nckh/nckh_pgdata:5432 hoặc DB bàn giao5454. Nếu cần DB integration, dùng clone test riêng sau một operation plan được root duyệt; không dùng dữ liệu thật của người dùng.

Catalog đọc từ `catalog_handoff_v1` với membership package đã pin; không mở cửa cho mọi raw listing. Đường mới chỉ đọc catalog, độc lập các API CRUD cũ. Không có view/package sai thì trả DATASET_NOT_READY, không fallback sang toàn bảng aggregate. Giữ đủ614room/168mini_house/3studio/4unknown, flags sang nhượng/partial/unknown;2tin thiếu tọa độ vẫn có trong danh sách nhưng không đặt pin.153area/636NULL không đồng nghĩa636nguồn thiếu diện tích.

Người dùng đã duyệt triển khai offline ngày 2026-10-04. Không crawl, migration, production write, bật Docker, trả phí, commit/push hoặc publish. Dùng dependency hiện có. Không chấm điểm an ninh, không dùng gần công an làm bằng chứng an toàn, không tạo xác suất ML, không thêm fullphone/review/identity.

## Hợp đồng nội bộ v1 cần khóa ở G0

- `TravelMode`: MOTORBIKE, WALK, BICYCLE, BUS. Mapping Google dự kiến TWO_WHEELER/WALK/BICYCLE/TRANSIT; phải xác minh tài liệu trước khi viết adapter wire. BUS là yêu cầu bus, không được coi một tuyến transit bằng tàu là bus.
- `Campus`: id khu_i/khu_ii/khu_iii, name, lat, lng, coordinate_version, verification_status. Tọa độ legacy chỉ là PROVISIONAL, chưa xác minh cổng. Backend là nguồn duy nhất cho frontend qua GET `/mobility/campuses`.
- `CatalogPage`: items, total, page, size (1..100). `CatalogListing` giữ id/source/source_id/housing_type/offer_kind, các trường nullable và flags; position gồm lat/lng/precision/source/verified_at, không tự suy precision từ số chữ số thập phân. GET `/mobility/listings` phân trang ổn định theo id; bbox là tham số riêng, không cắt catalog toàn bộ ở300.
- `RouteRequest`: listing_id, campus_id, requested_mode, departure_time nullable (RFC3339 cóoffset; BUS bắt buộc), direction cố định LISTING_TO_CAMPUS. Backend tự lấy hai tọa độ, không nhận URL/host tùy ý từ client.
- `RouteResult`: listing_id/campus_id, provider, requested_mode, effective_mode nullable, direction, status, duration_seconds nullable, distance_meters nullable, polyline nullable, observed_at nullable, coordinate_version, evidence_kind (NONE/SYNTHETIC_FIXTURE/LIVE), warnings[]. Không trả0phút khi thiếu tuyến; thiếu/malformed response không biến thành NOT_FOUND/NO_ROUTE.
- Status routing: NOT_CONFIGURED, CAPABILITY_UNVERIFIED, UNSUPPORTED_MODE, LOCATION_UNAVAILABLE, NO_ROUTE, RATE_LIMITED, PROVIDER_ERROR, OK. Không có key hoặc live_enabled=false thì NOT_CONFIGURED trước khi tạo HTTP client. Google capability registry theo endpoint+mode+region, mặc định UNVERIFIED; không suy unsupported chỉ vì chưa thử. ORS legacy vẫn tách biệt, không tự fallback.
- `NearbyRequest`: listing_id, radius_m thuộc500/1000/2000 (mặc định1000), categories thuộc grocery/market/pharmacy/healthcare/police/bus_stop. Đây là bán kính địa lý, không phải quãng đường đi bộ. Mapping Places type chỉ được điền sau khi đối chiếu tài liệu; không khẳng định mọi category đều được API hỗ trợ.
- `NearbyResult`: provider/status/evidence_kind, items[], queried_at nullable, center_precision, coverage (UNKNOWN/PARTIAL), truncated boolean. EMPTY là response rỗng hợp lệ; evidence_kind phân biệt SYNTHETIC_FIXTURE với LIVE. Disabled/error khác EMPTY. Kết quả trả về không chứng minh đã liệt kê mọi tiện ích trong bán kính.
- Status nearby: NOT_CONFIGURED, CAPABILITY_UNVERIFIED, UNSUPPORTED_CATEGORY, LOCATION_UNAVAILABLE, EMPTY, RATE_LIMITED, PROVIDER_ERROR, OK. EMPTY trong kiểm thử chỉ mô phỏng response rỗng với evidence_kind=SYNTHETIC_FIXTURE, không được trình bày như quan sát live. Unsupported chỉ dùng khi có bằng chứng không hỗ trợ; mapping chưa xác minh trả CAPABILITY_UNVERIFIED.
- `Place`: provider_place_id, name, category, lat/lng, straight_line_distance_m nullable, attribution; không lấy reviewtext/phone/photos/contactidentity. Không tự gán giờ mở cửa. Bản offline dùng tên/địa điểm tổng hợp có nhãn SYNTHETIC, không mượn Google logo cho dữ liệu tự tạo.
- `LocationWarning`: code, severity INFO/CAUTION, message, evidence_source, scope, observed_at nullable. Luật ban đầu: APPROXIMATE_LOCATION, LOCATION_UNKNOWN, ENTRANCE_UNVERIFIED, ROUTE_NOT_VERIFIED, PARTIAL_DESCRIPTION, TRANSFER_TERMS_UNVERIFIED, UNIT_TYPE_UNKNOWN. Không có cảnh báo không đồng nghĩa an toàn.

Đơn vị lưu/transport: giây và mét, tọa độ có tên lat/lng. Adapter xử lý thứ tự đặc thù provider. DTO TypeScript phải khớp Python, checked-in contract fixture chung. Route-to-three-campus là3kết quả độc lập, giữ lỗi/NULL riêng; không nhét các mode vào REAL[] cũ.

Các kiểu G0 phải định nghĩa trước khi giao worker: `Position` có lat/lng hữu hạn trong miền [-90,90]/[-180,180], precision/source/verified_at; `BoundingBox` gồm south/west/north/east cùng miền, south<=north và west<=east (không hỗ trợ cắt kinh tuyến 180). `ResolvedRouteRequest` chứa RouteRequest, origin Position, destination Campus; `ResolvedNearbyRequest` chứa NearbyRequest và center Position. Không chấp nhận một nửa cặp lat/lng. POST routes nhận một RouteRequest cho một campus; UI yêu cầu tối đa ba campus độc lập, không dùng batch ngầm.

Ngoại lệ legacy duy nhất trong scope: sửa chiều geometry thành trọ→campus để khớp Matrix và nhận phần tử NULL trong route_time_campus cùng consumer TypeScript. Không thay endpoint, provider mặc định hoặc các trường còn lại. “Giữ legacy” dưới đây không có nghĩa giữ hai lỗi này.

## Kiến trúc và ranh giới provider

Module mới `apps/api/app/mobility/`: contracts, catalog_repo, campuses, service, warnings, router; subpackage providers có base và google. Provider interface `async compute_route(request: ResolvedRouteRequest) -> RouteResult` và `async nearby(request: ResolvedNearbyRequest) -> NearbyResult`. Resolved request mang tọa độ do server xác minh cùngversion; network adapter không đọc DB.

### Khóa interface để các worker phối hợp

- `MobilitySettings` trong providers/base.py: enabled=False, live_enabled=False, server_api_key là SecretStr rỗng, timeout_seconds=10.0, region="VN"; capability modes/categories mặc định tập rỗng. Constructor provider nhận `config:MobilitySettings`, `transport:httpx.AsyncBaseTransport|None=None`. Transport được inject không có nghĩa tự bật live; chỉ transport tổng hợp mới có evidence_kind=SYNTHETIC_FIXTURE. Runtime không cấu hình transport này.
- `CatalogListing`: id:int dương; title, source, source_id; source_url/source_contact_url nullable; price/area/address/district/description nullable; images:list[str]; housing_type/offer_kind/description_state/description_completeness nullable; description_is_partial/unit_type_uncertain/offer_context_uncertain/mixed_use_possible/lease_transfer_terms_verified:bool|None; parsed_amenities:dict[str,bool|None]|None; position:Position|None. Không trả source_record hoặc nhận xét/danh tính vào DTO công khai.
- `Position`: lat/lng; precision thuộc APPROXIMATE/VERIFIED/UNKNOWN (mặc định UNKNOWN); source:str|None, verified_at:datetime|None. `Campus.coordinate_version="legacy-2026-07-06-provisional"`, verification_status="PROVISIONAL". `RouteResult.coordinate_version` lấy từ campus; `polyline` là list[Position] nullable, chỉ lat/lng được dùng để vẽ. `warnings` là list[LocationWarning]. Các thời gian trả về là UTC có offset hoặc NULL.
- `CatalogRepo(engine:Engine,package_id:str=PINNED_PACKAGE_ID)`: list_page(page:int=1,size:int=50,bbox:BoundingBox|None=None)->CatalogPage, get_listing(listing_id:int)->CatalogListing|None, get_position(listing_id:int)->Position|None. `CatalogPage.total` là số thuộc query sau bbox, `page/size` ổn định theo id. PINNED_PACKAGE_ID=ccd4bb988a93e6b676d2baa49de70d7e20a9b63c64a836bd673e514c95371d35; catalog_sha256=b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947. CatalogUnavailable được API map HTTP503; id không tồn tại HTTP404. Query chỉ view đã pin; không kết nối DB khi khởi tạo.
- `RouteService(catalog,provider).route(request:RouteRequest)->RouteResult` và `PlaceService(catalog,provider).nearby(request:NearbyRequest)->NearbyResult` là async; cả hai resolve id ở server. Campus không tồn tại bị validation reject HTTP422. Request chỉ chứa trường đã khai báo (extra=forbid). Các lỗi provider trả status có cấu trúc, exception thô không ra API.
- Campus registry: `CAMPUSES:tuple[Campus,...]`, `get_campus(campus_id:str)->Campus`; Python là nguồn của endpoint. Legacy CAMPUSES chỉ giữ để tương thích, không được dùng trong luồng mới. Bốn chế độ thuộc yêu cầu sản phẩm; status unsupported/unverified hiển thị riêng theo docs và pilot.
- NearbyResult gồm listing_id, radius_m, categories để UI kiểm request identity; Place.category dùng category nội bộ đã yêu cầu. Phân loại Places dùng mapping chính thức; một category không hỗ trợ phải báo rõ, không âm thầm bỏ category. `coverage=PARTIAL` cho response hữu hạn thành công, UNKNOWN cho error/disabled; không có trạng thái COMPLETE.
- Local fixture transport chỉ có trong tests và E2E harness. Không có fixture HTTP endpoint hay config fixture public trong app thường. Các constructor dịch vụ dùng duck-typed read-only catalog cho unit tests để không cần DB.
- BUS success phải có response transit step thực sự. Field mask thêm `routes.legs.steps.travelMode` và `routes.legs.steps.transitDetails.transitLine.vehicle.type`; chấp nhận BUS/INTERCITY_BUS/TROLLEYBUS, cho phép bước đi bộ nối tuyến. Không có transit step, thiếu loại phương tiện hoặc có rail thì PROVIDER_ERROR với measurement NULL; không gọi nó là BUS. Đây là kiểm tra yêu cầu BUS đã chốt, không suy mode chỉ từ request preference.

Google adapter chỉ được dùng injected httpx transport trong unit tests. Default app mode disabled; không mở endpoint fixture hoặc fixture-mode qua querystring trong app thường. E2E dùng server/harness riêng với cờ test-only, chặn egress. Với2tin thiếu vị trí, LOCATION_UNAVAILABLE/khônggọi provider.

Web có facade renderer. Giữ Leaflet/OSM legacy riêng; GoogleMapView lazy-load chỉ khi có browser key và tính năng live được duyệt. Không vẽ dữ liệu Google lên OSM hoặc lưu/cache Google data trước khi có kết luận policy cụ thể. Khi chưa có key, UI hiển thị trạng thái rõ ràng và panel offline, không gọi Maps SDK. Offline canvas/fixture không tạo HTTP tile hoặc SDK requests.

Các settings dự kiến: mobility_enabled=false, google_live_enabled=false, google_server_api_key="", browser key riêng giới hạnreferrer. Không đưa serverkey vàoNEXT_PUBLIC, URL,log,exception hay fixture. Chỉroot sửa config/main/package dependencies vàgate sau review. Payload routing không gửi title/description/contact, chỉtọa độ/phươngtiện/thời gian cầnthiết. Không log raw response.

Không lưu kết quả Google vào DB, snapshot, localStorage hoặc cache dùng lại giữa request trong giai đoạn này. Request-scoped transient processing phải tuân thủ policy đã đối chiếu trước live. Timeout/retry/rate limiting và idempotency chi phí được chốt ở G0; mặc định không retry tính phí, không gọi batch789. Request identity gồm listing/campus/mode/departure_time cho route và listing/radius/requested categories cho nearby; bất kỳ thay đổi nào phải hủy hoặc bỏ response cũ. Lỗi request cũ không xóa kết quả mới.

## Acceptance criteria

- [ ] AC1: catalog membership chính xác789, phân trang không trùng/mất; flags vàNULL giữ nguyên;2tin thiếu tọa độ không biến mất khỏi danh sách.
- [ ] AC2: một registry campus, hai đầu tuyến cùng chiều trọ→campus; không fallbackmode; từngcampus lỗi riêng; legacy schema nhận partialNULL mà không làmhỏng consumer cũ.
- [ ] AC3: không key/liveoff/capability chưa xác minh =>0networkrequest,0tính phí; fixture có nhãn và không đi vào runtime mặc định.
- [ ] AC4: adapter mapping/error/timeout/429/malformed/unit/polyline có test offline; kết quảOKfixture không được tính là hỗ trợGooglelive.
- [ ] AC5: tiện ích bán kính đúngđơnvị, categories đãkiểm chứng mapping; EMPTY khác UNKNOWN/error; không hứa exhaustive; không thu thập PII của người viếtreview/chủcơsở.
- [ ] AC6: cảnhbáo cócăn cứ; không có điểm an ninh/%ML. Gần công an chỉlàtiệních hỗtrợ.
- [ ] AC7: UI tránh response cũ, giữ nhãn provenance/mode/vị trí; không trộnGooglecontent vớiOSM khichưa duyệt policy; build/E2Eoffline có bằngchứng.
- [ ] AC8: khôngmutate sealed789 hoặcDBnguồn; reviewđộc lập, objectivegate mới trước triểnkhai nghiêmngặt; báo riêng nợtest cũ. Live giữ NOT RUN cho đến khi có key+capability/policyreview+budget/callcap+operatorGO.

## Verification plan

Lượt hiện tại chỉ kiểm tài liệu: cácfile nguồn được nhắc cóthật; interface/ownership/command nhấtquán; freshspec-critic trướccode. Không chạy gate Docker của mục tiêu cũ để chứngnhận plan mới.

TDD theo task; pytest offline chặn socket, DB và HTTP thật. Các lệnh: `python -m pytest apps/api/tests/test_mobility_contracts.py apps/api/tests/test_mobility_catalog.py apps/api/tests/test_mobility_routes.py apps/api/tests/test_mobility_places.py apps/api/tests/test_mobility_warnings.py apps/api/tests/test_mobility_api.py apps/api/tests/test_routing_legacy_contract.py -q`; `npm --prefix apps/web run build`; `npm --prefix apps/web run test:e2e -- --config=playwright.mobility.config.ts`. E2E dùng local fixture harness không external network; clone DB integration ở gate riêng. Full API rerun với PYTHONPATH=root có baseline 1046 passed/47 skipped/7 safe-backfill failed ngày 2026-10-04; báo riêng, không giảm gate để giấu. Các test mới chưa tồn tại tại thời điểm duyệt spec.

## Rollback / migration

Không migration ở foundation. Module mới sau featureflag defaultfalse; API/renderer legacy giữ nguyên cho đến integration được duyệt. Vô hiệu flag khôi phục luồngcũ, không rollback/sửa dataset789. Sau này nếu cần storage/cache/capabilitypersisted phải mởspec riêng cópolicy và migration/rollback. Mọi ngàygiá/quota/capability lấy từ nguồnchính thức cóURL+retrieved_at; chưa biết thì UNVERIFIED.
