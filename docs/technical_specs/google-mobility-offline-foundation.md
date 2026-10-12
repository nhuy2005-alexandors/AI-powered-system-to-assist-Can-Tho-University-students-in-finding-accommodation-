# Mobility foundation — as built

Updated: 2026-10-04. Offline implementation and measured checks are recorded below. Completion requires the matching objective receipt and final review recorded in CHECKPOINT.md. Google live and PostgreSQL integration NOT RUN.

## Data and API

`app/mobility/catalog_repo.py` reads only `public.catalog_handoff_v1`, with pinned package ID and catalog SHA256 from the approved spec. It checks789membership before each query and explicitly projects approved fields. It does not select or return the full source snapshot. Stable id-order pagination and bbox use the same membership/filter for both items and total.

Root independently converted the actual sealed JSONL through this reader's DTO conversion:789unique original IDs803..1597,614room/168mini_house/3studio/4unknown, two missing positions. ID order and every approved field matched input; catalog SHA b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947 unchanged. This verifies conversion, not SQL execution on PostgreSQL.

| Endpoint | Behavior |
|---|---|
| GET /mobility/campuses | Three backend-owned provisional campus records, coordinate version included. |
| GET /mobility/listings | page>=1,size1..100; optional complete south/north/west/east bbox; missing dataset returns503 DATASET_NOT_READY. |
| POST /mobility/routes | Server resolves listing/campus; MOTORBIKE/WALK/BICYCLE/BUS; BUS requires RFC3339 departure with offset; direction listing→campus. |
| POST /mobility/nearby | Server resolves center; radius500/1000/2000m; six documented categories; radius is geographic, not walking distance. |

Unknown listing returns404. Disabled mobility has no registered routes. Provider errors carry statuses and NULL measurements; missing data never becomes zero minutes or a valid empty observation.

## Providers and trust

Routes maps MOTORBIKE→TWO_WHEELER, WALK→WALK, BICYCLE→BICYCLE, BUS→TRANSIT. BUS preferences request only bus and response transit steps must use BUS/INTERCITY_BUS/TROLLEYBUS; walking access is allowed. Rail, missing transit proof or walking-only responses cannot be successful BUS results. Duration is seconds, distance meters, encoded polyline is decoded to named lat/lng positions.

Places uses Nearby Search New, selected field mask, maxResultCount20 and documented type mapping. It filters out-of-radius coordinates, rejects malformed/nonfinite coordinates before filtering, forwards only approved place/attribution fields and never phone/review/author payloads. EMPTY denotes a valid empty response; UNKNOWN coverage is used for unavailable/error states. Successful coverage is always PARTIAL; saturation signals possible truncation. No fictional pagination or exhaustive claim.

Both HTTP posts have a whole-request bound via asyncio.wait_for plus HTTPX timeouts, with zero retries. In this phase, shared request_gate allows only explicitly injected MockTransport for tests. Real transports remain blocked even with a key and live flag. All fixture results say SYNTHETIC_FIXTURE; no runtime fixture switch or endpoint exists.

Warnings are Vietnamese and evidence-based: unknown/approximate position, provisional entrance, unverified route, partial description, uncertain unit/transfer context and Google's beta route caution. Clear ordinary rental offers are not flagged as transfers solely because the transfer flag is NULL. Police proximity produces no security score or probability. VERIFIED positions require a source and offset-aware verification time. Returned evidence times normalize to UTC.

## Configuration

- Backend MOBILITY_ENABLED defaults false. MOBILITY_DATABASE_URL is a separate secret setting; missing it never reuses the legacy/default DB. Configured mobility engine is read-only. This turn opened no database connection.
- GOOGLE_LIVE_ENABLED defaults false and GOOGLE_SERVER_API_KEY is SecretStr. Supplying either does not remove the foundation's real-transport block. No key is included in fixtures, URLs, logs or frontend public environment.
- Frontend MOBILITY_ENABLED selects the new lane at request time. /map boots catalog/campus reads in the client; four dynamic same-origin proxies allowlist inputs and use no-store/generic errors. The legacy Leaflet/ORS flow remains separate.
- Source ZIP789 remains SHA25cbfca2a36adf2f93772a5e48db8f6a0a8b48e777de41668d7a4b4ee5911a4a. No schema/data migration or backfill was run.

## Verification record

- G1 fresh spec-critic APPROVE after four document corrections; G2 independent review APPROVE after causal contract fixes and nine shared Python/TypeScript DTO fixtures.
- Root focused backend command over all seven mobility/legacy-contract test files:120passed, one existing Starlette warning, exit0.
- Root full API diagnostic with PYTHONPATH=root:1166passed,47skipped,7failed in the same pre-existing safe-backfill tests, one warning, exit1. This is not a full-green claim.
- Fresh independent backend reviewer APPROVE; source and relevant acceptance assertions inspected. Reviewer did not rerun root's120tests.
- UI worker observed build exit0 and8/8Chromium tests pass with zero external browser attempts. Tests use synthetic IDs900001..900789, not sealed IDs. They cover789unique rendered rows across8pages,2no-coordinate rows retained, four modes, offset-aware bus time,3independent campus results, radius/categories, text escaping/contact URL checks and late success/failure races. Root inspected actual UI source and screenshot; root's final objective gate reruns these commands.
- A deliberate LIVE-render counterexample produced one forbidden polyline/POI node and failed the browser check; it was restored before final GREEN. Both render nodes and plot bounds exclude LIVE Google data. Only fixture route/POI geometry enters the temporary SVG canvas.
- Optional production browser smoke with MOBILITY_ENABLED unset was rejected by shell policy before execution; NOT RUN. Upstream HTTP status forwarding is source-inspected, not tested against a successful synthetic upstream server. These do not imply live readiness.
- Completion instrument: `node C:/Users/HUY/.agents/skills/init-framework/scripts/framework.js gate --root D:/Dev/Workspaces/NCKH`, using docs/.codex-gate.json, followed by framework check. It runs focused120backend tests, production web build and all8offline browser tests. The matching receipt is the authority; no old Docker receipt is reused. No live Google, DB integration, Docker, crawling, commit or push in this phase.

## UI boundary

The new workspace presents catalog/description/source contact, four transport choices, a local-time bus input, single/all-campus requests, and geographic-radius amenity controls. It uses generations, request identities and abort controllers to ignore stale results; departure time and requested categories are part of identity. It never substitutes zero for unknown measurement or driving-car for motorcycle.

With no Google key, a clearly labelled temporary coordinate diagram is available; it is not a street map. LIVE Google geometry/POI cannot enter that diagram. Names/measurements in a future live presentation still require Google attribution/display review before the live phase opens. No SDK or external tile is loaded in the tested new lane. Root removed developer-only tile/SDK/API wording from the student-facing copy before the final gate.

## Next phase boundary

Live work needs separate capability/display/policy/budget/pilot readiness. Country documents are not evidence of route availability at Cần Thơ. Google data must not be plotted on the legacy OSM map; no cross-request Google content storage is implemented. There is no ML confidence percentage or safety ranking. Legacy geometry direction and nullable per-campus route time were repaired narrowly without changing its default provider.
