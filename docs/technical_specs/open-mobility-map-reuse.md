# Selective open map reuse — implementation record

Date: 2026-10-07. Scope: local offline UI reuse for catalog789. Final acceptance is the matching objective receipt and independent review; this document does not certify live providers or a real catalog DB session.

## Implemented boundaries

- `apps/web/src/lib/map-ui.ts` extracts the donor's fixed red/green housing pins, campus star, fly-to/resize/scroll behavior, Vietnamese search normalization and price ordering. Donor MapInner/MapShell/ResultList and current mobility UI call the same helpers. Donor icons retain their cached instances.
- Existing `leaflet.markercluster`1.5.3 is promoted to a direct dependency without installation/version/integrity changes. The client imports both cluster styles and dynamically initializes Leaflet/plugin. Listing cluster adds synchronously with chunking/animation disabled.
- Original markers own immutable listing IDs. The container-local read-only snapshot observes actual `group.getLayers()` and `marker.getLatLng()`, preserves duplicate IDs for detection, rejects foreign/invalid layers and never derives its answer from source input. During user spiderfy, coordinates are temporary display positions; compare source coordinates initially or after unspiderfy and IDs throughout.
- One selection-only overlay uses the canonical DTO coordinate and fixed selected icon. It is excluded from original cluster membership. Selection stops the old fly, renders synchronously and focuses that coordinate. Filter replacement/destroy stop the old fly; retained selection is redrawn without a new focus. There is no programmatic cluster reveal queue. Both original/overlay popups disable auto-pan and create safe text/validated HTTP(S) links.
- Original and selected housing markers explicitly bind Enter keydown to the same selection callback as pointer click. Leaflet's `keyboard:true` alone focuses a marker and opens its popup; it does not select the Workspace row. The strengthened unselected-original-marker test exposed this omission before the root's bounded fix. Completion still requires the final gate and independent closure review for the repaired bytes.
- Search covers title/address, trims whitespace and matches Vietnamese accents/Đ. Price original/ascending/descending ordering preserves NULL-last and deterministic ID ties. Original total and filtered count are separate. Sorting changes only row order; map receives the memoized catalog-ordered filtered array.
- Filtering away the selected ID synchronously aborts/invalidates route and nearby requests, clears displayed results/selection, then applies the filtered view. Delayed replies cannot revive excluded results. Map/list selection shares the scoped scroll helper.
- Sidebar stays mounted while hidden; collapse/expand, keyboard and mobile/desktop resize preserve the map element, cluster/campus layers and selection. Pending chunk/init navigation has dedicated intercepted browser tests.

## Verification and source of truth

TDD and independent evidence are recorded in `.superpowers/sdd/2026-10-05-open-mobility-map-reuse-plan/`: baseline inventory, progress, renderer audit, approved overlay critique, view-controls report, backend-verification raw output, final-review and root-verification. The objective gate includes default old/new browser suites, explicit disabled/local-tile variants, Next build and the same11 backend mobility test files. Python gate entries use an empty task-owned temporary working directory to avoid loading real `.env`, a dummy DSN, disabled providers and no DB opt-in; only empty owned directories are removed.

Writer reuse15/15 and typecheck passed; root independently witnessed selection5/5 and helper6/6. Final default/build/variant results and receipt hashes belong to root-verification and the matching `docs/.framework-receipt.json`. These are synthetic offline browser measurements, not real-data/DB/provider coverage.

Latest full API diagnostic is1401passed/47skipped/16failed: seven historical safe-backfill signature/lock gaps and nine heldP1 acceptance-harness gaps. The11 focused mobility files passed227. Full API is not green.

## Next boundary

After matching final review/gate proof, resume P1 pin inventory and real cluster browser oracle using this frozen helper/renderer/donor/test set. P3 integration and P4 clone/live acceptance remain subsequent phases. Catalog/ZIP789 are immutable; real DB/Docker/provider/crawl operations were not part of this UI change.
