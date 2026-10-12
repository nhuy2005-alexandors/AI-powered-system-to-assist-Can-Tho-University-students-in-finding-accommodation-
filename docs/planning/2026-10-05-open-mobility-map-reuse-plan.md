# Open mobility map reuse — Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development with the existing native collaboration workflow. Root owns architecture/security/final diff; one GPT-6 Luna Max writer handles the bounded UI reuse phase, then a fresh GPT-6 Luna Max reviewer. The user authorized execution on 2026-10-06 after the design critique closed. No commit/push or Orca migration.

**Goal:** tái dùng code/tương tác map cũ phù hợp catalog789, không mở pipeline/route/tile legacy và không đánh mất safety guards P2.
**Architecture:** một shared UI-only helper module trích từ donor, được donor và native Leaflet P2 cùng gọi; native cluster dùng runtime1.5.3 đã cài. Workspace hiện tại giữ DTO/API/identity guards; kế thừa sidebar/viewcontrols và selection UX. Không đổi public MapProvider/backend/schema.
**Tech Stack:** existing Next14.2.35/React18/Leaflet1.9.4/leaflet.markercluster1.5.3/pytest/Playwright; không installation/network hoặc framework mới.
**Spec:** `docs/specs/open-mobility-map-reuse.md`.
**Status:** EXECUTION_APPROVED / VIEW_CONTROLS_IN_PROGRESS. User approved execution on 2026-10-06 and parallel independent lanes on 2026-10-07. Root freshly verified selection focused5; full UI/gate/review remain pending. Selected overlay amendment is recorded in the binding spec and requires fresh scoped critique/review. Parent plan resumes only after this amendment freezes and passes independent review.

## Global Constraints

- Catalog SHA256 b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947 and ZIP SHA25625cbfca2a36adf2f93772a5e48db8f6a0a8b48e777de41668d7a4b4ee5911a4a unchanged. Protect DB5432/nckh_pgdata and5454/nckh_handoff_789_pgdata; no DB/Docker/crawl/backfill/migration.
- Externalbudget0, including tiles/images/providers/realDNS. Browser only ownedloopback3031/installedChromium/interceptedsynthetic fixtures; no ComputerUse/download, key/auth/.env edits or credential reads.
- No Google production/fallback or Google-bearing geometry; OAuth untouched. WALK/BICYCLE exactORSprofiles, MOTORBIKE/BUS unsupported. No driving-car substitution, fakeML probability or police→safety score.
- MapProvider/publicDTO/API/backend/P0 policy/config fixtures frozen. Native UI-local subtype may add the specified readonly inspection method; no global writable map/group handle.
- Preserve dirty baseline and all unowned lanes. No gitreset/stash/checkout/commit/push/merge/deletion of donor/dataset. One writer, no nestedsubagents; reviewer only after writerfreeze.
- All P2 receipts archived as historical. Current UIcode after amendment needs fresh tests/review/gate; previous6checkPASS is not new acceptance.
- P1 RED retained/noGREEN; finalpin/oracle work waits for this amended UI freeze. P3/P4/P5 held. FullAPI historical10FAIL/47SKIP remain disclosed, not skipped to make this lane green.

## Review Focus

1. Filter/clear/unmount while Leaflet/plugin init resolves: stale group must not add old marker IDs or fire selection/provider requests; generation/destroy guard tests below.
2. Multiple listings at identical coordinates inside one cluster: each listing ID remains in actual group; clustercount is not catalogcount; reveal/select specific member works.
3. Null-price/null-area/null-position source rows: unknown labels and2NULL list membership retained, priceNULL last, no fabricated geometry/location/contact/risk.
4. Title/address/source link with hostile HTML/JS: fixed SVG palette only, popuptextescaped/textContent, URLsafe; no inline script or third-party image request.
5. Sidebar/viewport changes, keyboard marker selection and readonly snapshot lifecycle: no wrong map dimensions/leakedobserver/duplicateinstance or input-derived fake member report.

## Exact ownership and interfaces

One UI writer owns the following set only (root snapshots exact bytes and records HEAD before dispatch):

- Create `apps/web/src/lib/map-ui.ts` — donor-derived presentation/selection/search/price primitives, type-only Leaflet import, no I/O or eager DOM dependency.
- Modify `apps/web/src/app/map/MapInner.tsx` — import shared pin/focus/resize helpers; retain legacy public props and legacy TileLayer/campus/route plumbing outside reuse.
- Modify `apps/web/src/app/map/MapShell.tsx` — shared normalization/price helper only; no legacy API/radius/other sort rewrite.
- Modify `apps/web/src/app/map/ResultList.tsx` — shared scroll helper only; no legacy API/risk/image behavior rewrite.
- Modify `apps/web/src/components/mobility/leaflet-map-provider.ts` — actual clustered L.Marker housing layer, shared pin/focus/resize, safe popup, readonly snapshot/generation/cleanup. Preserve independent campus/route/POI layers and existing F1/F2 guards.
- Modify `apps/web/src/components/mobility/MobilityMap.tsx` — cluster CSS imports, readonly snapshot event bridge and cleanup; no request/provider authority change.
- Modify `apps/web/src/components/mobility/MobilityWorkspace.tsx` — donor-derived sidebar/search/price/synchronized selection UI; keep DTO/loading/route/POI/departure/AbortController/generation logic.
- Create `apps/web/src/types/leaflet-markercluster.d.ts` — side-effect module declaration only; minimal runtime-method types live UI-local near provider, no broad any/ts-ignore.
- Modify `apps/web/package.json`, `apps/web/package-lock.json` — promote only existing leaflet.markercluster1.5.3 to explicit direct dependency, keep existing integrity/resolved/other versions. No npm install/update.
- Create `apps/web/e2e/map-ui-primitives.spec.ts`, `apps/web/e2e/mobility-map-reuse.spec.ts` — helper behavior and realofflineUI reuse tests. Test-only fakes are labelled unit proof, not realLeaflet/DB evidence.
- Modify `apps/web/e2e/mobility-open-map.spec.ts` — strengthen listing membership from unclusteredDOMcount to actualgroup snapshot IDs/coords, keep sentinel/campus/provenance/tile/lifecycle cases.
- Modify `apps/web/playwright.mobility.config.ts` — add exactly the two new suites to existing testMatch, no runner timeout/reuseExistingServer/dependency workaround.
- Append `task-map-reuse-report.md` inside parent plan-owned SDD workspace.

No changes to mobility-offline.spec.ts or shared fixtures are necessary by default. If a stronger selector adjustment is actually required for preserved assertions, show the exact counterexample to root before expanding ownership; do not weaken/delete/skip a case.

Shared helper signatures frozen by root (the writer writes their bodies from donor code and tests):

```typescript
import type * as L from "leaflet";
export type PriceOrder = "original" | "price_asc" | "price_desc";
export function createHousingIcon(leaflet: typeof import("leaflet"), selected: boolean): L.DivIcon;
export function createCampusIcon(leaflet: typeof import("leaflet")): L.DivIcon;
export function normalizeMapSearch(value: string | null | undefined): string;
export function sortMapListingsByPrice<T extends { id: number; price: number | null }>(rows: readonly T[], order: PriceOrder): T[];
export function focusSelectedPosition(map: Pick<L.Map, "flyTo" | "getZoom">, position: L.LatLngTuple | null): void;
export function observeMapResize(map: Pick<L.Map, "getContainer" | "invalidateSize">): () => void;
export function scrollMapSelection(container: HTMLElement | null, listingId: number | null): void;
```

Readonly inspection interface in UI-local provider module (public MapProvider unchanged):

```typescript
type ListingMarker = L.Marker & { readonly listingId: number };
export type ListingLayerSnapshot = {
  generation: number;
  state: "READY" | "UNAVAILABLE";
  members: readonly { id: number; lat: number; lng: number }[];
};
// LeafletUiProvider = MapProvider & existing setCampuses + this readonly method:
getListingLayerSnapshot(): ListingLayerSnapshot;
// UI-only pure observation helper, called by that getter; no input-listings argument:
export function readListingLayerSnapshot(group: CatalogClusterGroup | null, generation: number, markerClass: typeof import("leaflet").Marker | null): ListingLayerSnapshot;
```

Member ID is a nonwritable own property on the actual marker. Getter reads currentgroup.getLayers()/marker.getLatLng, not listings input or a separate registry as oracle. Invalid/foreign layer, destroyed or uninitialized returns UNAVAILABLE. Sorted member array is not deduped. Register `mobility:listing-layer-snapshot` only on mapcontainer; CustomEvent detail `{respond:(snapshot:ListingLayerSnapshot)=>void}` gets a readonly value synchronously, no mutation/request. Wrapper removes listener on cleanup. No global debug map/group or test-only request flag.

## Task U-REUSE — one testable UI amendment

The steps below are sequential within one writer, not concurrent ownership lanes. Root sees first causal RED before product writes; after rootGREEN authorization incremental TDD within this approved set is allowed. One independent whole-amendment review after finalfreeze, not writer self-grading.

- [ ] **Step1 — record baseline and first RED.** Root snapshots all existing owned paths plus source/ZIP pins in the SDD workspace before dispatch; do not overwrite prior P0/P2/P1 baselines. Writer adds focused behavior tests first and stops before product edits. Missing helper/import must be an in-test failing assertion, not collectionerror. Root witnesses selected command/natural exit/cause.
- [ ] **Step2 — shared primitives, extracted not duplicated.** `test_shared_map_normalizes_vietnamese_title_and_address` asserts Đường/duong and null→empty. `test_shared_price_sort_keeps_null_last_and_source_immutable` covers bothdirections/ties/0price/originalorder. `test_shared_pin_palette_has_selected_and_campus_shapes` pins original fixedhousingred/selectedgreen/campusstar/no hostile text interpolation. `test_shared_focus_and_resize_cleanup` checks zoommax16/duration0.6/nullposition/disconnect; `test_shared_scroll_selects_the_requested_listing_only` tests ID/NULL handling. Extract donor bodies, wire donor imports, preserve existing contracts. Unit boundary fakes only prove helper behavior; realUI checks follow, no performance/live claim from a mock.
- [ ] **Step3 — direct cluster runtime, concrete version/type/CSS.** Add exactly leaflet.markercluster:"1.5.3" to packagejson and root lock dependencies; existing node_modules entry remains byte-equivalent version/integrity/resolved. No installation command. Add side-effect module declaration; UIlocal FeatureGroup extension declares getLayers/addLayers/zoomToShowLayer/getVisibleParent from installedJS. Dynamically register plugin client-only, runtime-check constructor. Import both exact clusterCSS paths in client MobilityMap; no ReactwrapperIcon.Default sideeffects/nativeCircleMarker misuse.
- [ ] **Step4 — native housing markers and getter.** RED `test_cluster_keeps_every_id_including_duplicate_coordinates` compares initial787actualmemberIDs/coordinates against fixture,789cards/2NULL, then zoom/spiderfy/reveal keeps sameIDs. Test snapshot computation with subset group members while source fixture has more rows; it must not report the input count. Nativegroup chunkedLoading=false/animate=false/addLayers synchronous; preserve currentmap/layerlifetime and pendinginitgeneration/destroy guards. `test_filter_clear_before_map_init_cannot_restore_stale_members` drives rapid query/clear/navigation and checks finalactualmember-ID set; no uncancellable bulk-add queue copied.
- [ ] **Step5 — bidirectional selection, original pin/popups, map dimensions.** RED `test_list_selection_reveals_cluster_member_and_focuses_map`, `test_map_selection_scrolls_and_selects_catalog_row`, `test_missing_position_selects_detail_without_fly_or_provider_call`, `test_sidebar_resize_keeps_map_layers_and_selection`, `test_keyboard_marker_and_sidebar_controls_work`. Use shared icon/focus/resize/scroll methods in actualP2calls. Selection updates icon/reveal without rebuilding campus/route/POI/group; mapresize on containerchange, not arbitrary testDOM removal. Preserve usablelist when tiledisabled/error. Popup shows title/price/address/precision/source safely; NULL unknown and campusPROVISIONAL remain. RED hostilepopup fixture proves script does not run; no image load.
- [ ] **Step6 — donor-derived view controls and sidebar.** RED `test_keyword_filter_matches_unaccented_vietnamese_without_catalog_refetch`, `test_price_sort_keeps_null_last_and_map_list_membership_equal`, `test_filtered_out_selection_cancels_late_route_and_nearby`, `test_clear_filter_restores_789_and_two_unpositioned_rows`. Extract old controls/layout into currentworkspace, not a parallelpage. Query handler computes nextvisibleIDs; if selectedID is excluded, call existing cancelRoutes()/cancelNearby() and setSelectedListingId(null) synchronously before applyingview. Thus displayed route/nearby as well as inflight identities are cleared; avoid delayed-effect-only cancellation. Sort/collapse preservevisible selection. Keep originaltotal789 plus separatefilteredcount; defaultcounts/IDs/NULLvaluesunchanged. No nearest/quality sort, legacyradiusquery, riskbadge, auto-route-on-click or sourceimage fetch.
- [ ] **Step7 — current regression and new assertion parity.** Replace only clustered-member assertions in mobility-open-map.spec with readonlyactualsnapshot checks, not inputdata/fakeDOMcount. Keep campusDTOsentinel, originalall8offlinecases, route/POIpositive+negativeprovenance, F1mixedtiles/recovery, F2missing/malformed/impossibletime+GoogleMaps/google_routes, unmount/races. Default runner executes old+new suites; disabled/localtile conditional variants must actuallyrun. No skips/deleted assertions. Unitpurehelpers do not certify actual787markers; browserfixtures do not certify realDB/catalog.
- [ ] **Step8 — freeze/report/root verification.** Fullownedpaths/SHA/donor-before/after/importcall-site list, exactRED/GREEN commands/naturalexits and all unrunlimits. Run TS/build/offlinebrowser default+disabled+localtile and focusedbackend unchanged; root runs finalfullAPIdiagnostic separately. Take/review currentdesktop/mobile/cluster/selection/collapse screenshots. Explicitly freeze after checks, release3031 and ownership before root reads actualdiff and dispatches freshreviewer. No edits afterfreeze; additionalfixes are scoped original-writer loops with causaltests, not silentcandidatechanges.

## Task ROOT-CLOSE — review and parent plan integration

- [ ] Root reads actualdonor/helper/renderer/workspace/package/lock/testdiffs, checks sourcehashes and screenshotprovenance; freshnativeGPT6LunaMax reviewer did not implement. Review eachAC and hostile/duplicate/stale/SSR counterexample; report PASS only with actualcommands, no borrowedP2receipt.
- [ ] After UIreusefreeze and review, resume original P1 with updated explicitpinset covering map-ui.ts, declaration, donorchanges, newtests/config/package/lock, amendment spec/plan. Independently enumerate expectedpins and mutate each newentry in isolatedtemporarytrees; do not self-derive expectedinventory from productiondiscovery.
- [ ] P1 actualbrowser uses readonly actualcluster snapshot members plus realAPI/source-derived789card/title/area/coordinate/2NULL/id980/source assertions. No fakecatalog/route/POI body in P4. Keep type-strict receipts/19table+viewdigests/cloneinspect/ACL/DMLrefusal. Root updates acceptance receiptfields in a separatelycriticked P1contract if needed; no fabrication of REALreceipt.
- [ ] ParentPUBLIC_ARTIFACTS remains exact parentopenspec/parentplan/.codex-gate.json and trustedreviewedcataloggateSHA; code manifest explicitly pins both reuseamendment files as well. Newpinsemantics/closedreceipt changes require freshreview; do not replace gate digest from untrustedreceiptorcurrentgate. Existingreviewedgate7/8templates unchanged until rootreviews actualcompletephasechecks.
- [ ] P3 integrates after P1 GREEN/freshreview; exactfinalofflinegate covers defaultold+newUItests and all guard/providerchecks, freshmatchingreceipt. P4 clone5455/API8032/UI3032 and P5externalrequests remain separatelyauthorized phases, not sideeffect of this UIplan.

## Verification commands

Windows browsercleanup uses the already witnessed exact-ownedloopback require_escalated workaround; no globalTimeout/reuseExistingServer or processkill outsidetask. Store commands in reports; never mask failedexit with a later command.

- Cwdapps/web: `node node_modules/@playwright/test/cli.js test --config=playwright.mobility.config.ts --grep 'shared_map|shared_price|shared_pin|shared_focus|shared_scroll'` for helperstage; exact testnames use those prefixes so grep must select nonzero tests.
- Cwdapps/web: `node node_modules/@playwright/test/cli.js test --config=playwright.mobility.config.ts` defaultalloldsuites+two newfiles. `node node_modules/typescript/bin/tsc --noEmit`; `node node_modules/next/dist/bin/next build` with NEXT_TELEMETRY_DISABLED=1.
- Disabled/localtiles: same explicitargv/env variants from allP2gate; P2UI_TEST_MAP_DISABLED=true/webmobilityfalse OR localtilestrue/httpsloopbacktileURL/intercepted before send. Both must countactualtests/nonzero selection; set allother testenv knobs deterministically.
- Backendenvironment PYTHONPATH=D:/Dev/Workspaces/NCKH, PYTHONIOENCODING=utf-8, PYTHONDONTWRITEBYTECODE=1. Existing11filemobility suite then final `D:/Dev/SDKs/Python/python.exe -m pytest apps/api/tests/ -q --tb=line -p no:cacheprovider` diagnostic; allfailures/skips named. NoDBtest opt-in/service/start.
- Docs: `node C:/Users/HUY/.agents/skills/init-framework/scripts/framework.js check --root D:/Dev/Workspaces/NCKH`. This validates docs only, not productreuse or realdata acceptance.

## Execution handoff

User requested GPT-6 Luna Max and approved this exact plan on 2026-10-06. Root preserves that model/effort for writer/reviewer, does not silently substitute5.6, and does not restart finishedP2 tasks. Safe handoff includes spec/plan, actualreuse inventory, red/green/diff/review/gate evidence and explicitreal/live limits.
