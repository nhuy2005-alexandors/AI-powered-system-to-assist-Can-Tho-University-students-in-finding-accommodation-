# Open mobility — kế thừa map open-source hiện có

Date: 2026-10-06. Status: SELECTIVE_REUSE_EXECUTION_APPROVED_BY_USER / INDEPENDENT_DESIGN_CRITIQUE_APPROVED / TDD_IN_PROGRESS.
Documentation tier: standard. Product implementation follows the approved design/plan, TDD and independent review; no completion is inferred before those checks run.
Parent contract: `docs/specs/open-mobility-migration.md`.
Approved implementation plan: `docs/planning/2026-10-05-open-mobility-map-reuse-plan.md` (user authorized execution on 2026-10-06).

## Intent and authority

Người dùng yêu cầu kiểm tra map open-source đã dựng và kế thừa phần phù hợp với hướng catalog789 hiện tại. Thành công không phải dùng cùng tên Leaflet: code trình bày và các tương tác cũ còn tốt phải được tái dùng thực sự, không dựng một map song song rồi gọi đó là kế thừa.

Root đã đọc các donor MapInner/MapShell/MapView/ResultList, renderer/workspace/DTO mới và dependency đã cài. Đây là kiểm toán nguồn, chưa phải browser acceptance của thiết kế này. Không có graphify graph sẵn; không tạo graph, cài dependency hay gọi mạng để trả lời câu hỏi tái dùng.

P2 đã đạt gate offline cho phiên bản trước amendment, không chứng nhận UI kế thừa này. P1 đang dừng sau RED, chưa sửa harness; cần chốt UI kế thừa trước khi pin inventory/real browser oracle cuối. P3/P4/P5 không tự mở. Không reset/stash/checkout/commit/push; giữ mọi dirty change và donor cũ.

## Kiểm toán donor và quyết định tái dùng

| Phần hiện có | Bằng chứng source | Quyết định cho hướng hiện tại |
| --- | --- | --- |
| Leaflet/react-leaflet/cluster | apps/web/package.json; app/map/MapInner.tsx:6-16 | Đã có dependency. Không đổi stack hay tải thư viện mới. |
| Pin đỏ, pin chọn xanh, campus icon | app/map/MapInner.tsx:24-49 | Tách primitive thuần để donor và renderer mới cùng gọi; SVG chỉ có hằng số style, không ghép title/address vào HTML. |
| Gộp marker/chunked loading | app/map/MapInner.tsx:129 | Tái dùng engine Leaflet.markercluster; giữ đủ member, không đếm cluster là số tin. Native catalog789 không dùng internal chunkedLoading vì queue đó không hủy được khi filter/destroy; không tuyên bố đã tái dùng chunking. |
| Bay tới tin được chọn | app/map/MapInner.tsx:54-64 | Tái dùng hành vi flyTo/max(currentZoom,16), mở marker đang trong cluster; không bay tới tâm giả cho tin thiếu vị trí. |
| Resize sau đổi sidebar | app/map/MapInner.tsx:68-78 | Tách ResizeObserver/invalidateSize cho cả hai renderer; disconnect khi unmount/destroy. |
| Map chọn tin thì list cuộn theo | app/map/ResultList.tsx:21-30 | Tái dùng helper scrollIntoView; list chọn tin và pin chọn tin dùng cùng selection callback. |
| Tìm tên/địa chỉ không dấu | app/map/MapShell.tsx:21-27,47-54 | Tách hàm tìm kiếm dùng chung; thêm test Đường/duong vì code cũ chưa đổi đ→d, không chỉ sao lại comment. |
| Giá tăng/giảm | app/map/MapShell.tsx:55-69 | Tái dùng sắp xếp client-side, NULL cuối ở cả hai chiều, tie-break deterministic; không mutate danh sách gốc. |
| Sidebar và nút thu/mở | app/map/MapShell.tsx:169-177,218-227 | Giữ tương tác/layout responsive của donor; map resize đúng, vẫn truy cập được nút mở và chi tiết/tuyến/POI. |
| Popup tiêu đề/giá/địa chỉ | app/map/MapInner.tsx:139-158 | Giữ nội dung hữu ích, đưa vào DOM textContent/React; thêm nhãn precision thật và link nguồn an toàn. |
| Dynamic client-only | app/map/MapView.tsx:6-14 | Giữ cơ chế không SSR Leaflet; hiện P2 cũng có client-only lifecycle, không thay bằng import server. |
| Ba campus | app/map/campuses.ts; app/mobility/campuses.py | Giá trị cũ đã được kế thừa. UI vẫn dùng Campus DTO fetch, không mang mảng hardcode vào renderer; PROVISIONAL không bị nâng thành VERIFIED. |
| Bộ lọc tin nearby cũ | app/listings/repo.py:136-146 | KHÔNG tái dùng: limit300 và cleaned/phong_tro làm mất catalog789/mini_house/studio. |
| Route cũ/chọn tin tự fetch | app/map/MapShell.tsx:75-87; app/listings/routing.py:18 | KHÔNG gọi từ lane mới: driving-car không phải xe máy. Giữ route button/mode/identity/AbortController của P2 và provider guard. |
| Rank gần trường/chất lượng | app/map/MapShell.tsx:10-15,63-69 | Chưa có các trường tương ứng trong CatalogListing. Không dựng điểm hoặc distance giả; không mở các sort này trong amendment. |
| Chip radius quanh campus | app/map/MapShell.tsx:19,154 | Không bê query legacy; chưa thiết kế cách xử lý vị trí gần đúng/2NULL. Giữ POI radius500/1000/2000 hiện tại, không đánh đồng hai loại bán kính. |
| Risk badge “An toàn” | app/map/ResultList.tsx:44; lib/format.ts:22-29 | KHÔNG tái dùng ngữ nghĩa: chưa có chứng cứ an ninh. Giữ unknown/location warnings, không suy điểm từ công an/POI. |
| Giá NULL/ảnh tải tự động | lib/format.ts:3-4; app/map/ResultList.tsx:109-115 | Giữ “Giá chưa rõ”, không suy NULL=thỏa thuận. Giữ ảnh URL trong data; không tự tải ảnh bên thứ ba khi external budget0. |
| Link detail nội bộ cũ | app/map/ResultList.tsx:95; app/map/MapInner.tsx:151 | Không giả định API listing cũ có cùng contract/catalogmembership. Giữ MobilityDetails và source/contact URL an toàn hiện tại. |

Các đường dẫn app/map và lib trong bảng tính từ apps/web/src; backend tính từ apps/api. Bằng chứng là code đã đọc trong lượt này, không dựa vào trạng thái checkbox cũ của Map_Routing.md.

## Lựa chọn kiến trúc

1. **Tái dùng có chọn lọc, khuyến nghị:** tách primitive và UI thuần từ donor để cả donor và P2 sử dụng, đưa cluster/pin/fly/resize/search/sort/sidebar vào workspace hiện tại. Giữ nguyên P2 data/provider/lifecycle/race/evidence boundary. Đây là reuse code/tương tác, không rollback sang pipeline cũ.
2. **Đổi hẳn về MapShell/MapInner:** tái dùng layout nhiều hơn, nhưng ListingOut/CatalogListing, route_time/risk/hardcodedcampus/tile auto-load đều khác. Phải tách lại các boundary đã kiểm; nhiều rework và rủi ro mất guard. Không chọn làm mặc định.
3. **Chỉ giữ thư viện và viết lại tương tác:** ít đụng donor nhưng không đáp ứng yêu cầu kế thừa thật. Không chọn.

Người dùng đã chốt “tái dùng có chọn lọc” khi được cung cấp đường dẫn written design này. Những quyết định kỹ thuật dưới đây đóng các thiếu sót do critic chỉ ra, không đổi hướng đã chọn. Critic closure và exact implementation plan review vẫn cần trước implementation. Không mở rộng MapProvider/publicDTO/backend/API/schema/DB. Không có contract ListingOut giả được tạo từ CatalogListing.

## Scope và tái dùng thực sự

- Tách một module UI-only, không I/O, dự kiến `apps/web/src/lib/map-ui.ts`: tạo icon từ palette cố định; normalize search; focus selected position; observe resize/cleanup; scroll selected row. Leaflet instance đi qua tham số/type-only import, không eager import window/document khi SSR.
- Donor MapInner dùng lại helper icon/fly/resize đã tách; MapShell dùng normalize đã tách; ResultList dùng scroll helper đã tách. Giữ public props/luồng legacy của donor; không “cải tiến” backend legacy hay riskbadge cũ ngoài lane này.
- P2 renderer/workspace dùng chính helper ấy. Không chỉ copy thêm một bản tương tự rồi gọi là reuse. Native Leaflet factory/setter contract hiện tại được giữ; React wrapper tiếp tục quản lý lifetime và các lớp độc lập.
- Chốt plugin path: promote `leaflet.markercluster` đúng **1.5.3** từ transitive thành direct dependency trong apps/web/package.json và root package entry của lock; giữ integrity/resolved/version của entry đã có. Không npm install/download/update, không thêm @types package. Dynamic import client-only sau Leaflet init; không import react-leaflet-cluster wrapper trong native P2 renderer vì wrapper sửa Icon.Default toàn cục. CSS trong client MobilityMap import đúng `leaflet.markercluster/dist/MarkerCluster.css` và `leaflet.markercluster/dist/MarkerCluster.Default.css` đã có.
- Chốt type boundary: `apps/web/src/types/leaflet-markercluster.d.ts` khai báo side-effect module, không pretend có @types đã cài. UI-local type `CatalogClusterGroup` extends Leaflet FeatureGroup và chỉ khai báo runtime methods đã đọc từ plugin1.5.3: getLayers(), addLayers(), zoomToShowLayer(), getVisibleParent(). Native Leaflet namespace được narrow/runtime-check constructor plugin một lần; không any/ts-ignore cho toàn renderer. Build/type và actual browser integration xác minh module/constructor/CSS; đây là type strategy được chọn, chưa phải compile proof.
- Listing markers dùng L.Marker/divIcon phù hợp engine cluster, không nhét CircleMarker vào plugin không hỗ trợ. Campus/route/POI vẫn ở lớp riêng. Selection cập nhật marker/reveal/focus, không rebuild campus/route/POI hoặc mất cluster/listing members. Popup không copy raw HTML từ nguồn.
- Amendment 2026-10-07 after measured reveal failures: selected presentation uses one separate Leaflet marker in a selection-only feature group. Original immutable listing markers remain in the cluster and remain the sole snapshot membership oracle. The overlay is placed at the selected DTO coordinate with fixed selected icon and safe popup; it never counts as another catalog member. Selection/filter replacement/destroy clears the old overlay and pending reveal callbacks. Actual map-to-list selection is tested from an original rendered cluster member; duplicate-coordinate selection is independently tested by list-to-overlay interaction plus unchanged cluster membership. Root authorized this bounded presentation change after the installed plugin's zoom cleanup repeatedly removed a freshly spiderfied original; no geometry or public provider contract changes.
- Scoped audit refinement (fresh GPT6LunaMax critique APPROVE_AS_DESIGN): selected overlay is rendered synchronously from the currently selected DTO; focus also uses that DTO's canonical coordinates. List selection no longer starts `zoomToShowLayer` or programmatic spiderfy. Changing selection/filter/destroy stops the owned Leaflet fly animation before replacing presentation; both original and overlay popups use `autoPan:false` so opening either cannot interrupt the explicit focus. Filtering while the selected row remains visible redraws its overlay without restarting focus. Cluster interaction still uses its normal public UI. Snapshot deliberately reports actual `getLatLng()` values: while the plugin is spiderfied these are temporary display positions, and they must return to the original coordinates after unspiderfy. Initial/settled source-coordinate assertions and all-time ID membership assertions remain distinct. Snapshot never substitutes source input for actual marker layers or writes temporary positions into data.
- Chốt batching: native listing group có **chunkedLoading=false, animate=false**; addLayers đồng bộ với dataset hiện tại tối đa789. Không giữ closure/timer internal bulk-add qua filter hoặc destroy. Import/init callbacks có generation+destroy guard trước khi ghi active group. Thay visible-ID set thì increment listing generation, clear/rebuild chỉ listinggroup; selection-only thay icon/reveal, không rebuild group. Chưa đưa ra cam kết performance; đo actual789 trong browser, tối ưu scheduler có thể hủy là thiết kế riêng nếu có vấn đề đo được. Donor legacy giữ cấu hình chunk cũ ngoài scope, không tuyên bố sửa race của legacy.
- Keyword/price sort thực hiện trên toàn catalog đã fetch. Hiển thị tổng catalog và số kết quả đang lọc riêng. No-filter giữ đúng789IDs,787positionedmembers/2NULL; không mất tin chỉ vì vị trí thiếu. Filter chỉ là view, không sửa dataset hay gọi lại legacy nearby; clear khôi phục đủ789.
- Search chỉ title/address; normalize NFD, bỏ combining accents, lowercase và đ→d. Sort options trong amendment: nguyên thứ tự catalog, price_asc, price_desc. Hai price sort luôn NULL cuối và tie bằng ID tăng dần; không suy NULL=0. Map/list cùng nhận một visible-ID set. Selection còn visible thì giữ; nếu search loại selection thì clear selection và cancel route/nearby generations/controllers trước khi áp view mới, không gửi request mới. Sorting và sidebar-collapse không reset selection; clearsearch khôi phục catalog nhưng không tự chọn tin hoặc tự gửi provider request.
- Sidebar-collapse không unmount map hoặc xóa selection/route/nearby; ResizeObserver cập nhật kích thước. Pin→list và list→pin là hai chiều; chọn tin không gửi route/POI tự động. Giữ manual route actions và toàn bộ identity/race guards hiện có.

### Read-only cluster inspection boundary

Mỗi housing marker là UI-local `ListingMarker = L.Marker & { readonly listingId: number }`; gán listingId own property bất biến từ ID được DTO validate khi tạo marker. Không nhét ID vào geometry fake/array placeholder hoặc suy ID từ title/DOM. Campus/POI marker không có property đó và không thuộc listing cluster.

UI-local LeafletUiProvider subtype thêm `getListingLayerSnapshot(): ListingLayerSnapshot`, không sửa shared MapProvider. Snapshot dạng `{ generation:number, state:'READY'|'UNAVAILABLE', members: readonly {id:number,lat:number,lng:number}[] }`. Getter đọc **active CatalogClusterGroup.getLayers()**, kiểm mỗi layer là ListingMarker hợp lệ và đọc lat/lng từ marker.getLatLng(); sắp ID nhưng không dedupe, để duplicate bị nghiệm thu bắt. Không đọc listings input/marker registry làm đáp án. Foreign layer/invalidmember, destroyed hoặc init chưa xong trả UNAVAILABLE, không tự điền expected counts.

UI-only reader `readListingLayerSnapshot(group: CatalogClusterGroup|null, generation:number, markerClass: typeof import('leaflet').Marker|null): ListingLayerSnapshot` được export tại provider module và dùng bởi getter; không nhận input listings. Leaflet chỉ type-import ở module scope. Unit tests dùng structural group/marker fakes để phân biệt subset/foreign/duplicate/invalid data và kiểm getter gọi getLayers; browser tests mới là bằng chứng actual Leaflet/cluster. Không gọi mock group là real renderer proof.

Wrapper cài một read-only listener trên chính mapcontainer: `mobility:listing-layer-snapshot`, CustomEvent detail `{ respond:(snapshot:ListingLayerSnapshot)=>void }`. P4/test page.evaluate gửi event và nhận getter result đồng bộ. Không expose map/group/constructor/writehandle qua window/global hoặc serverendpoint; listener không đổi selection/layers và không gọi provider/DB/network, disconnect khi cleanup. Snapshot chỉ có public ID/coordinate đã hiển thị, không description/contact/secrets. Việc lấy snapshot không phải quyền sửa group hay acceptance bypass.

Test phân biệt getter thật với báo cáo từ input: unit getter chạy với một actual group chỉ có subset markers trong khi input fixture vẫn đủ; browser duplicate-coordinate clusters/zoom/reveal không mất IDs; rapidsearch/clear/unmount trước import completion không làm stale group sống lại. P4 so sánh snapshot member IDs/coordinates với source-derived expected DTO, không tự tin từ stateREADY/count đơn lẻ. Không giả787DOMnodes để giữ assertion cũ.

## Acceptance criteria

- [ ] **AC1 — Reuse provenance:** actual diff cho thấy helper được trích từ donor, donor và P2 đều import/call. Giữ trước-sau baseline donor/P2; không xóa code/user changes hay viện cùng dependency làm proof reuse.
- [ ] **AC2 — Membership:** initial catalog789 và nguyên IDs/NULL; markercluster chứa đúng787memberIDs, không trùng/mất/ghim2NULL. Oracle lấy ID từ actual marker layers trong group, không từ input/listing count hoặc fake787 DOM nodes. Zoom/spiderfy/click/reveal và duplicate coordinates không làm mất member. P4 kiểm source-derived IDs sau, không fake receipt.
- [ ] **AC3 — Selection:** chọn list bay tới tọa độ DTO và hiện đúng một selected overlay tại tọa độ đó; original cluster membership không đổi. Chọn original pin trên map hoặc selected overlay cuộn/chọn đúng row; chọn2NULL vẫn xem detail/source, không fly/route/POI. Keyboard hoạt động. Không force zoom/font/layout tùy tiện để test xanh.
- [ ] **AC4 — Layout:** sidebar-collapse/expand và viewport mobile→desktop khiến actual Leaflet size đúng, map không tạo thêm instance/leakobserver; route/POI/campus/selection còn. SSR/build và navigate away/back không window-is-undefined hoặc pendinginit layer leak.
- [ ] **AC5 — View controls:** Đường/duong search tên/address có test; priceNULL cuối cả hai chiều, ties deterministic; input data không mutate. Đổi/clear filter không gửi thêm catalog/provider requests; total789 và filteredcount phân biệt. Không quảng cáo nearest/quality nếu không có measurement.
- [ ] **AC6 — Truth/privacy:** price/areaNULL giữunknown; không “An toàn”/fakeconfidence/ảnh request. Campus DTO sentinel/name/coords/PROVISIONAL vẫn đúng. Popup/title/address/link hostile không thực thi script; source/contact giữ chính sách hiện có.
- [ ] **AC7 — Preserve P2 safety:** thiếu/malformed/impossible observation time hoặc Google-bearing source không vẽ; null-source/openSYNTHETIC positive có label. F1 mixedtileerror và latergoodbatch recovery giữ. Unsupported MOTORBIKE/BUS và manual request semantics giữ; late response/unmount/campus/mode/departure/radius/category tests không bỏ/skip/loosen.
- [ ] **AC8 — Verification:** causal RED trước từng thay đổi checkable; Next build/type, default+disabled+localtile browser, screenshots/interaction và fresh independent review sau writerfreeze. Existing DOM-count oracle phải đổi có chủ đích khi pin clustered: ID-set actualmembers mạnh hơn visiblepin count, không chỉ bỏ assertion.

## Acceptance harness, sequencing và protected artifacts

P1 source chưa sửa; extension RED9FAIL/33PASS/95deselected đã được worker báo, root chưa witness đầy đủ và chưa GREEN. Hold P1GREEN/P3/realclone trong lúc design reuse chưa approved. Không “đóng P1” với inventory trước khi helpers/plugin/CSS/tests xuất hiện.

Sau approval/designplan/review và UIreusefreeze: P1 thêm explicit pins cho shared helper, dependency/type/CSS nếu có, donor files đã đổi, regression tests và amendment spec/plan theo exact reviewed manifest. Parent PUBLIC_ARTIFACTS vẫn pin parent open spec/plan/supported cataloggate; parent sẽ tham chiếu amendment và codepins phải ràng buộc bytes của amendment. Không âm thầm thay trustedcataloggate SHA hoặc tạo REAL receipt để lách prerequisite.

Browser P4 oracle phải nhận actualcluster members đồng thời kiểm DOMcards/title/area/source links/2NULL và selectorid980. Sharedhelper/donor/renderer tests pin độc lập. Rerun exact inventory và gate review sau UIreuse trước P3/P4, giữ all19table+view digests/leastprivilege/type-strict receipts. Offlineunit không chứng nhận DB/provider.

Catalog SHA b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947 và ZIP SHA25cbfca2a36adf2f93772a5e48db8f6a0a8b48e777de41668d7a4b4ee5911a4a bất biến. DB5432/nckh_pgdata và5454/nckh_handoff_789_pgdata bảo vệ; không DB/Docker/crawl/network/auth/credential/commit/push/merge. Externalbudget0, kể cả tile/ảnh. Offline browser chỉ task-ownedloopback và intercepted synthetic transport đã có.

## Verification plan

- Backend unchanged: existing11filemobility focused suite; acceptanceguard initialRED riêng, không claim fullAPIgreen. LastfullAPI1368PASS/47SKIP/10FAIL là snapshot lịch sử, cần fresh run cuối.
- Cwdapps/web: `node node_modules/typescript/bin/tsc --noEmit`; `node node_modules/next/dist/bin/next build`; existing `node node_modules/@playwright/test/cli.js test --config=playwright.mobility.config.ts` cùng disabled/localtile variants và reuse tests plan sẽ chỉ rõ.
- Root/framework phasegate must be reviewed/promoted/approved/run for actual finalbytes; allP2 receipt cũ giữ nguyên làm lịch sử, không authenticate newhelper/UI.
- Rollback chỉ owned diff qua review, không gitreset/checkout/stash/delete dataset. Trong lỗi map vẫn giữ usablelist/details; không fallback Google/legacy300/publictile. Không xóa donor cũ hoặc tắt cả app.

## Execution authorization

User selected the selective-reuse written design and subsequently authorized the exact implementation plan on 2026-10-06. Execution is now limited to the plan-owned UI reuse files, starts with an independently witnessed causal RED, and still requires GREEN, root diff inspection, full scoped verification and a fresh reviewer before completion. P1 GREEN/P3/P4/P5 remain held until this amendment freezes.

Independent nativeGPT-6 Luna Max critic closure: APPROVE_AS_DESIGN after both material findings resolved. It read installedplugin getLayers and readonlyboundary; no compile/browser/product acceptance run, and no planexecution authorization. Root incorporated its reminder that filtering away selection clears displayed route/nearby as well as cancelling inflight requests.
