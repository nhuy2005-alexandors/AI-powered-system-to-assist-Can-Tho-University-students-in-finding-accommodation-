# Approved bounded local demo policy — 2026-10-11

Scope: catalog789 read-only clone5455 only; no public deployment or batch geocoding. User deliberately approved these demo providers on 2026-10-10/11. Endpoints fixed by `demo_policy.py`; no credential in this document. A provider policy record is not proof of runtime success.

| Capability | Fixed endpoint | Pilot attempts | Identification / attribution |
| --- | --- | --- | --- |
| WALK/BICYCLE | https://api.heigit.org/openrouteservice/v2/directions/{profile}/geojson | 2 (one each) | ORS key server-only; openrouteservice / HeiGIT |
| Nearby pharmacy,1000m | https://overpass-api.de/api/interpreter | 1 | NCKH-Tro-CTU/0.1; OSM contributors / Overpass |
| Public landmark lookup | https://nominatim.openstreetmap.org/search | 1 plus one cache hit | App UA/contact URL; OSM contributors / Nominatim |
| Visible interactive map | https://tile.openstreetmap.org/{z}/{x}/{y}.png | <=60 per session | App UA + accurate Referer; visible OSM attribution |

All backend providers: approved immutable policy expiry2026-12-31UTC, content-bound digest, manifest ceiling30/provider/process, single worker/concurrency1, <=1request/s/provider, deadline10s/connect2s, <=1MiB response, no retry/redirect. The ceiling is not permission to spend30 calls. Operator pilot sends only counts above. Stop rather than rotate hosts or bypass limits. Demo provider can be disabled via configuration; no SLA/coverage guarantee or production entitlement claimed.

## Official policy sources checked

- [Nominatim usage](https://operations.osmfoundation.org/policies/nominatim/), checked2026-10-11: app-wide1rps, interactive moderate use, no autocomplete/systematic queries, identifiable client, cache repeats, attribution, no personal/confidential data. Developer/user deliberately chose this bounded use; not a generic geocoding service.
- [OSM tile usage](https://operations.osmfoundation.org/policies/tiles/), checked2026-10-11: HTTPS, attribution, accurate Referer, honor caching headers, no no-cache/prefetch/offline bulk or headless pan/zoom scanning. Pilot uses visible single view and ordinary single-listing UI selection, not a sweep. Private runtime tile cache honors max-age/Age/Expires or7days when absent; max128files/1MiB each. No tile archive handed to team.
- [ORS terms](https://account.heigit.org/info/tos), reached2026-10-11 via official terms link; dynamic terms body was not retrievable by text tool. Exact current account quota/billing and provider retention were NOT VERIFIED. Prior authorized direct WALK/BICYCLE returned200; this is no assertion of legal entitlement or zero billing. Pilot itself is bounded2calls, no quota workaround or automated retry.
- [Overpass project/API documentation](https://wiki.openstreetmap.org/wiki/Overpass_API), checked2026-10-11. Public service best-effort; OSM data/license attribution applies. No full coverage claim. Exact retention of operator logs NOT VERIFIED.

## Outbound data inventory and retention limits

Routing receives approximate listing coordinates plus provisional campus coordinates and mode. POI receives approximate center,1000m radius and pharmacy tags. Geocoder receives only the public landmark “Can Tho University” and bounded Cần Thơ viewbox. Tiles receive viewer IP,Referer and tile bounds. No listing ID/title/description/source contact, seller identity, DSN or key is sent to OSM endpoints. ORS credential is sent only in its authenticated server request header.

Local receipts contain aggregate counts/status/timestamps/distances plus source/policy hashes, no addresses/contact/credentials or raw provider payload. Geocode cache lives only in app memory,128entries/24h; tile assets remain in owner-only runtime per provider cache policy. Neither is catalog enrichment. Provider-side data retention/secondary-use was not fully verified; do not infer privacy guarantees or general sharing authority from this demo approval.

## Operation gates and stop points

Before first outbound: independently review code+manifest, verify matching current P4 real-catalog receipt, inspect fixed Docker identity/mapping and read-only role, compare catalog and all public-table digests before/after. Run one uvicorn worker8033 and owned Next3033, no production main/crawler. Frontend receives only closed allowlisted environment; no key/DSN. Stop owned servers/browser afterward; preserve databases5432/5454/5455 and all volumes. Report NOT_VERIFIED for any unmet check. NO_MATCH/AMBIGUOUS demonstrates geocoder operation, not a verified address/location.

Manifest preparation runs a controlled fresh Next build and compares reviewed source pins before/after. Approved private manifest binds compiled BUILD_ID/server/static/JSON artifacts. Pilot compares same source/build bindings again before PASS, in addition to unchanged data digests. Tile cache freshness uses max(Age, apparent age from Date), subtracts that from max-age or Expires lifetime, and returns remaining cache lifetime rather than renewing it.
