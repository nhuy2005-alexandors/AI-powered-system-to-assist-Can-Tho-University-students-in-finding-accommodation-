# Open mobility replacement — Implementation Plan

> For agentic workers: use superpowers:executing-plans for solo execution or superpowers:subagent-driven-development when the root dispatches bounded lanes. Checkboxes track observed work, not predicted results. Do not implement until the written spec/plan is accepted for execution.

**Goal:** thay Google-production bằng Leaflet + open adapters trên catalog789, không làm lại dữ liệu.
**Architecture:** giữ endpoint/DTO/domain mobility; factory chọn disabled/ORS/Overpass/Nominatim. UI Leaflet dùng DTO, không nhúng quyết định provider vào business logic. Google historical adapters không đăng ký production.
**Tech Stack:** existing Python/FastAPI/httpx/Pydantic, Next/React/Leaflet, pytest/Playwright; chưa thêm dependency hay self-host.
**Spec:** `docs/specs/open-mobility-migration.md`.
**Status:** EXECUTION_APPROVED / P2_GEO_UI_REVIEW_APPROVED, 2026-10-05; P0/ORS/Overpass have historical scoped review/gate evidence. GEO/UI independently approved after finding closure; allP2 gate proof is tracked separately in CHECKPOINT/ledger, not inferred from review. Network/DB execution has not begun; P1/P3 and later real/live acceptance remain pending. Resume actual completed tasks from the plan-owned progress ledger, not unchecked historical task bullets.

**Pending user-requested amendment:** `docs/specs/open-mobility-map-reuse.md` records the actual donor audit and proposed selective code/UI reuse. Written-design review/approval and an exact implementation amendment precede those product changes. P1 is stopped after its RED extension (no harness GREEN); its final pin inventory and real-browser oracle must wait for the revised UI freeze. P3/P4/P5 remain held. Completed allP2 offline phase evidence is retained, not reused as certification of the amendment.

## Global Constraints

- Catalog SHA256 b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947; ZIP SHA25625cbfca2a36adf2f93772a5e48db8f6a0a8b48e777de41668d7a4b4ee5911a4a unchanged. No crawl/backfill/migration.
- Protect original5432/nckh_pgdata and handoff5454/nckh_handoff_789_pgdata. No source compose/down-v/prune/reset, commits/push/merge or other-lane edits.
- All external traffic default off, including tiles. Never Google fallback; hosted open data is not unlimited free hosting. Provider policy and live operation approval precede traffic.
- Root owns architecture, shared DTO/config, gate and operational decisions. Native GPT-6 Luna Max is the requested subagent model; no silent5.6/provider substitution. At most two independent writers alongside root; reviewer runs after writers stop.
- No borrowed receipt/PASS. Preserve dirty baseline; every worker is not alone and may edit only its exact write-set. Missing authorized prerequisite ends that lane with evidence, not an invented fallback.

## Review Focus

1. Real-looking LIVE Google payload on Leaflet: reject by provider AND provenance; covered P0/P2UI.
2. Switching selected listing/mode/radius while requests race: ignore late successes/errors; P2UI.
3. HTTP200 Overpass with runtime-error remark/partial body: must not become EMPTY; P2POI.
4. Same source row differing only bool/int/float, missing table from both digests: fail acceptance; P1/P4.
5. Endpoint DNS/private redirect or simultaneous quota requests: fail before unauthorized send; P0 plus adapter tests.

## Task order and ownership

Quy ước đường dẫn rút gọn chỉ trong bảng: `providers/*` và `router.py` nằm dưới `apps/api/app/mobility/`; `tests/*` là `apps/api/tests/*`; `app/main.py` là `apps/api/app/main.py`. Các đường dẫn `apps/web/*` và `scripts/*` tính từ repo root. Không được tự chọn thư mục khác khi nhận write-set.

| Task | Depends on | Exact write-set / deliverable |
| --- | --- | --- |
| P0 contract/factory policy | spec+plan approval | `apps/api/app/mobility/contracts.py`, `providers/base.py`, new `providers/open_config.py`, `providers/registry.py`, `providers/network_policy.py`, `apps/api/app/config.py`, `app/main.py`, mobility `router.py`, `warnings.py`; `apps/web/src/lib/mobility-contracts.ts`, new `map-provider.ts`; shared fixtures `apps/api/tests/fixtures/mobility/`, `apps/web/e2e/mobility-fixtures.ts`; contract/API/warnings tests and new `test_mobility_provider_policy.py`. Root-owned serialized task. |
| P1 acceptance repair | P0 + all P2 source present/frozen | `scripts/mobility_catalog_acceptance.py`, `apps/api/tests/test_mobility_catalog_acceptance_guard.py`, `apps/web/e2e/mobility-catalog-acceptance.cjs`; no product source. |
| P2ROUTE | P0 | new `providers/ors_routes.py`, `tests/test_mobility_ors.py`, `tests/fixtures/open_mobility/ors/`. |
| P2POI | P0 | new `providers/overpass_places.py`, `tests/test_mobility_overpass.py`, `tests/fixtures/open_mobility/overpass/`. |
| P2GEO | P0 | new `providers/nominatim_geocoder.py`, `tests/test_mobility_geocoder.py`, `tests/fixtures/open_mobility/geocoder/`. |
| P2UI | P0 | new `apps/web/src/components/mobility/MobilityMap.tsx`, `leaflet-map-provider.ts`; modify `MobilityWorkspace.tsx`, `MobilityDetails.tsx`, `apps/web/src/app/map/page.tsx`, `apps/web/src/lib/config.ts`; new `apps/web/e2e/mobility-open-map.spec.ts`; `apps/web/playwright.mobility.config.ts` selects both suites. Bounded renderer/Google-label assertion updates allowed in `apps/web/e2e/mobility-offline.spec.ts`, retaining all8cases/membership/NULL/races/Google-rejection, no skips or weakening. No changes to backend/contracts/shared fixtures or Google-key worktree. |
| P3 integration | all P1/P2 lanes | root integrates registry/main/router wiring and shared fixture/API assertions after ownership release; updates existing `tests/test_mobility_routes.py`, `test_mobility_places.py` only as needed to keep historicalGooglefixtures explicit, not delete coverage; full scoped diff review. |
| P4 real catalog | P3 offline green+review | root-only operational clone5455/API8032/UI3032; no shared DB; requires P1/P3 to extend and verify ALL new adapter/map/e2e pins and new artifact bindings first; existing harness does NOT yet bind them. |
| P5 provider pilot | prepare after P3; execute only after P4 PASS + separate policy/operation approval | root owns new `docs/planning/open-mobility-provider-policy.md`, `scripts/open_mobility_pilot.py`, `scripts/open_mobility_tile_pilot.cjs` plus tests; no traffic until actual endpoints/budgets chosen and P4 verified. |
| P6 closeout | P4; P5 if claiming live | root docs/technical_specs/open-mobility.md, checkpoint and matching scoped gate; fresh independent final review. |

Schedule after P0: P2ROUTE+P2POI, then P2GEO+P2UI; freeze all P2 writers, then P1→P3 serial. P1 runs after adapters exist because actual harness inventory scans their directory while guard tests assert a static expected pin set. Rerun that comparison again after P3 integration and before P4. Root may reorder independent P2 pairs, never share writable paths. If more worktree isolation is needed, choose it explicitly without moving dirty changes or checking out teammates' branches. No merge authorization implied.

## P0 — freeze interfaces and disable Google runtime

Consumes existing DTO/RouteProvider/PlacesProvider. Produces the exact contract/settings/MapProvider defined in spec for every later lane. Add simple Disabled providers and factory registration using lazy imports only for selected open adapter; missing implementation must fail closed, not silently choose Google.

- [ ] Write RED `test_no_google_provider_when_old_key_and_flags_present`: old Google flags/key present, instantiate application/router, issue route/nearby; no Google constructor/network calls, safe NOT_CONFIGURED or configuration rejection. Preserve Google OAuth config.
- [ ] Write RED `test_open_provider_config_rejects_unknown_and_google`, `test_private_endpoint_and_redirect_rejected`, `test_atomic_budget_prevents_second_send`, `test_response_size_limit`, `test_contract_provider_attribution_cross_language`. Assert exact profile/provider/NULL/evidence semantics from spec, not file text.
- [ ] Run policy+contract+API tests, record failure causes before code.
- [ ] Implement OpenMobilitySettings and policy gate. Protocols/DTO addition as spec; GeocodeResult validation has one deterministic semantics. Set RouteResult/NearbyResult neutral defaults and explicit provider on historicalGooglefixture adapters/results. Factory DI remains available for offline tests, never a request-controlled provider URL.
- [ ] Freeze ProviderPolicy, RequestPolicyGate.claim and RequestPermit.send signatures/fields exactly as spec. App-level shared counter+semaphore, no per-request reset. Test missing/expired/hash-mismatched policy and simultaneous claims before send. Provider adapters consume this shared gate, not three independently invented network guards.
- [ ] Implement pure `policy_digest(policy:ProviderPolicy)->str` with exact canonical serialization excluding policy_sha256 as spec. Tests use literal canonical bytes and rejection after any field change or self-declared digest; trusted expected digest lives separately. No self-referential or caller-approved policy hash.
- [ ] Pin MapConfig and attribution validation. No new `MapLibre` dependency. Expose only tile URL/origin/attribution to UI; ORS/provider secret stays server-only.
- [ ] Run tests GREEN and publish a concise contract handoff with signatures/types/paths. Freeze these paths until P3; independent reviewer before downstream workers if behavioral diff is substantial.

## P1 — close known acceptance defects without weakening proof

Consumes frozen P0 DTO. Produces guarded acceptance harness, still no real receipt.

- [ ] Reproduce current `test_remediation_serve_api_observes_clone_before_engine` and `test_remediation_native_acl_snapshot_is_parseable_without_modifying_acl`. Fix source cause: inspect target before engine in serve-api, correct PowerShell ACL command syntax. Do not loosen ACL or reorder test assertions to mask failure.
- [ ] Keep wrongtarget CLI test reaching config validation through its TEST-ONLY seam; production has no bypass flag. Confirm malformed CLI stays one generic JSON line/exit1/no input echo.
- [ ] Add RED code-pin tests on actual final P2 inventory. Extend `CODE_PIN_FILES` explicitly with `apps/api/app/config.py`, `apps/api/app/main.py`, `apps/web/src/lib/map-provider.ts`, `apps/web/e2e/mobility-open-map.spec.ts`, `apps/web/e2e/mobility-offline.spec.ts`, `apps/web/e2e/mobility-fixtures.ts`, `apps/web/playwright.mobility.config.ts` and four new backend test files (`test_mobility_provider_policy.py`, `test_mobility_ors.py`, `test_mobility_overpass.py`, `test_mobility_geocoder.py`). Directory discovery already covers new Python adapters and mobility components, but static `CODE_PIN_PATHS` in guard tests must enumerate them too; include new open_mobility fixture files in the exact manifest. Mutate each omitted config.py/main.py/source/test/fixture pin and missing table on both sides; each must fail.
- [ ] Replace `PUBLIC_ARTIFACTS` exactly with `docs/specs/open-mobility-migration.md`, `docs/planning/2026-10-05-open-mobility-agent-plan.md`, `.codex-gate.json` containing reviewed catalog-phase content promoted from `.codex-open-mobility-catalog-gate.json`. Framework only accepts supported filenames. Root archives previous actualgate/receipt bytes+hash before each phase promotion. Until catalog-phase actual gate hash is independently approved, real verification fails closed; old Google/P0/offline gate cannot satisfy it. Mutation tests for old-spec/old-plan/wrong-phase-gate and missing artifact must fail even with recomputed unrelated hashes. Record this as TO IMPLEMENT, not existing behavior. No raw payload/DSN/key in receipts.
- [ ] Extend actual browser expectations for Leaflet without loading external tiles in real-data acceptance: local neutral test tile/stub may serve map base only, never fake catalog/route/POI responses. Compare every title/area and actual789IDs from sealed source; retain id980 withheld behavior and two no-coordinate cases.
- [ ] Run acceptance guards GREEN. Root reviews actualdiff and receipt-schema changes before future P4 use. Historical Google/offline receipts stay untouched, unapproved root gate is not a bypass.

## P2ROUTE — ORS adapter

Produces `ORSRouteProvider(settings:OpenMobilitySettings, *, transport:httpx.AsyncBaseTransport|None=None)` implementing `compute_route(request:ResolvedRouteRequest)->RouteResult`. Uses P0 network policy, no legacy routing caller or route_time_campus write.

- [ ] RED `test_walk_uses_foot_walking_and_lng_lat`, `test_bicycle_uses_cycling_regular`, `test_motorbike_and_bus_send_zero_requests`, `test_route_missing_position_precedes_provider`, `test_units_no_route_rate_limit_and_malformed_nulls`, `test_profile_attribution_and_provenance`.
- [ ] Expected outgoing path `/v2/directions/foot-walking/geojson` or `/v2/directions/cycling-regular/geojson`, origin listing→campus, duration seconds unchanged, distance meters unchanged, exact effective_mode on OK. Valid BUS request includes departure_time; unsupported response has no measurements.
- [ ] Implement exact status mapping and bounded HTTPX transport. Build fixtures from synthetic payloads, no Google content or external calls.
- [ ] GREEN focused tests; reviewer checks coordinate order, no implicit driving-car, deadline/body cap/zero retry and provider allowlist. Release files for P3.

## P2POI — Overpass adapter

Produces `OverpassPlacesProvider(settings:OpenMobilitySettings, *, transport:httpx.AsyncBaseTransport|None=None)` implementing `nearby(ResolvedNearbyRequest)->NearbyResult`; internal pure `build_overpass_query(request)->str` from fixed enums/numeric coordinates only.

- [ ] RED tests `test_fixed_tag_query_for_six_categories`, `test_node_way_relation_ids_and_centers`, `test_radius_filter_and_dedupe`, `test_101_items_marks_truncated_returns_100`, `test_remark_or_partial_json_not_empty`, `test_private_tags_not_exported`, `test_empty_is_partial_observation_not_full_coverage`, `test_generic_or_rail_platform_is_not_bus_stop`. Bus platform needs bus=yes unless highway=bus_stop; verify query and response parser.
- [ ] Implement mapping/query caps and P0 network policy. IDs and attribution as spec; malformedcenter/errorremark fail, not hidden as missing POI.
- [ ] GREEN tests including429/timeout/oversize. No persistent cache or dependency on a public Overpass instance before P5 policy approval.

## P2GEO — isolated geocoder seam

Produces `NominatimGeocoder(settings:OpenMobilitySettings, *, transport:httpx.AsyncBaseTransport|None=None)` implementing `geocode(GeocodeRequest)->GeocodeResult`. P0/P2 expose no new production endpoint. Approved P5 amendment permits explicit POST lookup only in isolated demo app with `demo_geocode_enabled=True`; never crawler/backfill/autocomplete.

- [ ] RED tests `test_address_and_bbox_validation`, `test_zero_one_many_candidates`, `test_viewbox_order_and_bounded_query`, `test_out_of_bounds_and_malformed_position`, `test_no_verified_precision_without_evidence`, `test_missing_policy_zero_http`.
- [ ] GET search/jsonv2/limit5/bounded=1 per spec; exact one valid bounded result→OK/APPROXIMATE, multiple→AMBIGUOUS/positionNULL, empty→NO_MATCH; partial malformed result fails entire response, not cherry-pick.
- [ ] GREEN tests; assert no repository write caller or fallback centroid. Leave production disabled until endpoint policy and exact sanitized sample approved.

## P2UI — Leaflet renderer on catalog789

Consumes P0 MapProvider/DTO/settings and current `/mobility/*`; never consumes legacy `/listings/nearby` for catalog membership. Produces createLeafletProvider and React wrapper with dynamic client-only import.

- [ ] RED browser tests:789cards/787pins (including clustered members)/2unpositioned; tile-disabled and tile-failure retain usable list; null area not0; selected partial/withheld flags and source link correct; attribution visible; LIVE Google geometry/POI rejected.
- [ ] RED late-response tests for listing/mode/campus/radius/category changes and unmount; map destroy removes only owned listeners/layers. Do not lose prior abort/generation safeguards.
- [ ] Implement Leaflet rendering with existing installed dependency. Only allowlisted ORS/OSM payloads draw; external tile URL defaults empty; fixture/local neutral tile only in e2e setup, never fake catalog in P4. Mark fixture evidence visibly in test-only scenarios.
- [ ] RED `test_map_disabled_never_falls_back_to_legacy_tiles_or_300_row_filter`; then replace `/map` false-flag branch with local-only unavailable state. Keep old MapShell source/backend intact but not automatically selected. No dependency on public OSM tile URL while new tile settings are absent.
- [ ] Keep four mode choices but clearly mark MOTORBIKE/BUS unsupported; do not substitute a mode. BUS request contract still validated; no route button should send a disguised car request.
- [ ] Run existing8 plus new offline Playwright cases, Next build, browser screenshots for review. Tests assert zero external attempts, no Google SDK import or oldMapskey effect. Browser install/traffic remains subject to execution permission, not part of this planning turn.

## P3 — integrate, gate and review

- [ ] Integrate released adapters in registry; wire server-only settings in main and test app, keep missing config disabled. Preserve legacy flows without importing their Google key or300-row filter.
- [ ] Add cross-provider API tests and fixture parity checks; no Google renderer/content cross-contamination, source_snapshot never reaches response. No schema or membership change.
- [ ] After all adapter/UI/P1 changes stop, reconcile and run actual `discover_source_pin_paths` against guard `CODE_PIN_PATHS`; no test pass from earlier partial inventory counts as coverage of subsequently created files. Include new spec/plan/catalog-gate binding tests separately from offline gate receipt.
- [ ] Prepare `.codex-open-mobility-offline-gate.json` template with focused all-mobility/legacy tests, new provider/policy/guard tests, build and BOTH offline browser suites. Archive prior actual `.codex-gate.json` and receipt bytes/hash, then promote template into supported `.codex-gate.json`. Historical .claude-gate/docs-gate unchanged. Future checkpoint Tierstrict uses supported actualgate for OFFLINE_READY; independent review and approval precede running it.
- [ ] Run fullAPI separately and report known/new failures by name. Investigate any new failure; existing7safe-backfill failures do not become silently skipped or accepted as green.
- [ ] Stop writers, root inspects actual diff and fresh independent reviewer reproduces counterexamples. Only matching candidate hashes and commands permit OPEN_MOBILITY_OFFLINE_READY.

## P4 — real catalog acceptance, no external services

- [ ] Root revalidates Docker daemon/image pin, source/ZIP hashes, ports5455/8032/3032 and absence of target container/volume. Docker not responding is NOT proof no resources exist. No worker starts Docker or resets resources.
- [ ] Use the protected operation rules in `docs/specs/mobility-catalog-live-acceptance.md` for clone identity/labels, private path/ACL, fresh passwords, reader flags/grants,19table+view digests and DML refusal. New open spec supersedes provider/UI expectations, not isolation safeguards. Any broader schema/runtime change returns to operation review.
- [ ] Start only task-owned testAPI/Next, live providers+external tiles off. Run revised actual-source789 harness, no catalog mocking. Real receipt binds new code pin set/spec/plan/config/operation, not old Google bindings. Preserve earlier receipts before any new gate writes.
- [ ] Before real acceptance, root creates/reviews `.codex-open-mobility-catalog-gate.json` template retaining offline checks and adding actual receipt verification; archive previous actualgate/receipt, promote this template into supported `.codex-gate.json` and bind its reviewed catalog-phase hash as third PUBLIC_ARTIFACTS entry. Missing actual receipt fails, never skip. This gate proves real catalog/API/UI with external providers off; P5 network pilot evidence is separate and not inferred from its PASS.
- [ ] Root and independent reviewer inspect real receipt/screenshot/digests; safe cleanup only owned UI/API children, preserve clone. No clone/source data migration. Record CATALOG789_REAL_ACCEPTANCE_VERIFIED independently of provider pilot.

## P5 — bounded provider readiness and pilot (runtime operation gated)

This task has a separate runtime operation gate: P4 receipt + approved policy/budget must pass before traffic. Endpoints are fixed to the approved 2026-10-10/11 manifest, never chosen or rotated by a worker to unblock itself.

- [ ] Fill `docs/planning/open-mobility-provider-policy.md` with exact endpoint/owner/official policy URLs+checked date, quotas/rate rules, required attribution/caching/User-Agent, request/data retention and zero-cost constraint. Browser tile endpoint must be reviewed too. If caching is mandatory, stop/revise cache design before requests; don't claim compliance from not caching.
- [ ] Include explicit `outbound_data_inventory`: listing/campus coordinates to routing/POI; sanitized addresses to geocoder; viewer IP and map/tile bounds to tile host; source IDs/names/descriptions/contact never sent. Record each provider's retention/secondary-use terms and root's minimization/disclosure decision. Unknown/denied external-sharing permission leaves that provider budget0. Convert approved policy to immutable ProviderPolicy records and pin their hashes outside untrusted request payloads.
- [ ] Approved 2026-10-10/11 bounded smoke:1 WALK and1 BICYCLE on one catalog listing/campus,1 nearby request radius1000m,1 public landmark geocode plus identical repeat (1 backend attempt/1 cache hit), one browser session max60tile requests. Manifest ceiling30/provider/process is not a batch authorization. Zero automatic retries; attempts count failures too. One backend worker/no reload; stop on ambiguity, no quota circumvention/host rotation. Cache canonicalization/TTL/LRU/cancellation and aggregate stats follow spec P5 detail; cache/API tests must discriminate incorrect bounds reuse, expired approval reuse and aliased result mutation.
- [ ] Before first external request, assert P4 real-catalog acceptance PASS for the same sealed789/candidate, plus separately approved policy manifest and budget. Preparation may overlap P4; execution may not. No P3 mock/offline receipt can satisfy this prerequisite.
- [ ] `scripts/open_mobility_pilot.py` + `tests/test_open_mobility_pilot_guard.py` TDD: immutable approved manifest, endpoint/config/source/code hashes, budgets checked atomically before send, report redacts keys/addresses. Test over-budget/concurrent attempts/mismatched endpoint/wrong modes/missing policy all reject before HTTP. Single-worker pilot only.
- [ ] `scripts/open_mobility_tile_pilot.cjs` + `apps/api/tests/test_open_mobility_tile_pilot_guard.py`: real-browser route interceptor claims integer counter before await/continue, max60attempts, spacing>=1s, deadline90s, abort request61 and stop. Test concurrent/fake61route calls, unapproved origin/path/template and retry attempts; no actual browser or traffic in guard tests. Pilot uses this runner rather than opening unrestricted production UI. Production hosting quotas remain a separate deployment requirement.
- [ ] Exact pilot code manifest includes SHA-256 of `scripts/open_mobility_pilot.py`, `scripts/open_mobility_tile_pilot.cjs`, both pilot guard test files and every source/config/dependency file those runners execute. Root-pinned approved manifest is verified against actual bytes before first backend/tile send; missing/changed tile-runner hash aborts before request1. Result receipt binds this approved manifest hash plus actual runner hashes. Test changed/omitted runner bytes with fake send guard. P5 write-set explicitly includes both scripts as listed in task table; no unpinned substitute runner.
- [ ] Reviewer examines operator code/policy before run. Record successes/no-route/429/errors/p50/p95 and manual route plausibility separately from correctness. No 5sample→all789 coverage claim. Confirm campus entrance manually before ever promoting PROVISIONAL.
- [ ] Motorbike/bus remain unsupported; future provider/profile/transit dataset requires separate capability design and evidence. Geocoding returns observations only, no update of source positions or missing areas.

## P6 — closeout

- [ ] Fresh exact-candidate independent review after writers stop; root reads real diff/output. Framework check plus appropriate scoped gate(s), no borrowed approval.
- [ ] Write `docs/technical_specs/open-mobility.md`: what runs, config names without keys, attribution, unsupported modes, measured versus unknown coverage, and how to disable providers.
- [ ] Update checkpoint only to achieved level. Hand off source/runbook + immutable dataset links; actual deploy/new Docker application bundle/commit/push/public release is not authorized by this plan.

## Verification commands (run at owning task, not predictions)

PowerShell session preparation:

```powershell
$env:PYTHONPATH='D:/Dev/Workspaces/NCKH'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
```

- Existing contract baseline: `D:/Dev/SDKs/Python/python.exe -m pytest apps/api/tests/test_mobility_contracts.py apps/api/tests/test_mobility_catalog.py apps/api/tests/test_mobility_routes.py apps/api/tests/test_mobility_places.py apps/api/tests/test_mobility_warnings.py apps/api/tests/test_mobility_api.py apps/api/tests/test_routing_legacy_contract.py -q --tb=line -p no:cacheprovider`
- P1: `D:/Dev/SDKs/Python/python.exe -m pytest apps/api/tests/test_mobility_catalog_acceptance_guard.py -q --tb=line -p no:cacheprovider`; expected0failed, no skip masking. Existing98 count is baseline, not fixed future threshold.
- Each P0/P2 owner: same pytest invocation with its exact new test file listed above. Nonexistent file is NOT RUN/FAIL, not successful empty suite.
- Full diagnostic: `D:/Dev/SDKs/Python/python.exe -m pytest apps/api/tests/ -q --tb=line -p no:cacheprovider`.
- Web build (cwd apps/web): `node node_modules/next/dist/bin/next build`.
- Offline browser (cwd apps/web): `node node_modules/@playwright/test/cli.js test --config=playwright.mobility.config.ts` (config updated to select both suites).
- Actual receipt: `D:/Dev/SDKs/Python/python.exe scripts/mobility_catalog_acceptance.py verify-receipt --runtime-dir D:/Dev/Data/NCKH/mobility-catalog-acceptance-20261004-01` after P4 revised pins/schema; never substitute offline receipt.
- Docs: `node C:/Users/HUY/.agents/skills/init-framework/scripts/framework.js check --root D:/Dev/Workspaces/NCKH`.

Always preserve command exit status; do not chain a later successful command that hides pytest failure. Workers return owned paths, RED/GREEN commands+exit codes, checks not run, remaining risks and ownership release. No agent self-certifies live readiness.
