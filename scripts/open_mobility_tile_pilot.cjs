"use strict";
const path = require("node:path");
const fs = require("node:fs");
const timers = require("node:timers");

async function settleWithin(task, timeoutMs) {
  let timer;
  try {
    return await Promise.race([
      task.then(()=>true,()=>false),
      new Promise(resolve=>{timer=timers.setTimeout(()=>resolve(false),timeoutMs);}),
    ]);
  } finally { timers.clearTimeout(timer); }
}

async function drainRoutes(active, deadline) {
  while (active.size) {
    if (!await settleWithin(Promise.allSettled([...active]),Math.max(1,deadline-Date.now()))) return false;
    if (Date.now()>deadline && active.size) return false;
  }
  return true;
}

function tileParts(raw) {
  let u;
  try { u = new URL(raw); } catch { return null; }
  const m = /^\/(0|[1-9]\d*)\/(0|[1-9]\d*)\/(0|[1-9]\d*)\.png$/.exec(u.pathname);
  if (u.origin !== "https://tile.openstreetmap.org" || u.search || u.hash ||
      u.username || u.password || !m) return null;
  const parts = m.slice(1).map(Number);
  const [z,x,y] = parts;
  return z<=19 && x<2**z && y<2**z ? parts : null;
}

class TileCache {
  constructor(directory) {
    fs.mkdirSync(directory,{recursive:true,mode:0o700});
    if (fs.lstatSync(directory).isSymbolicLink()) throw new Error("Invalid tile cache");
    this.directory = directory;
  }
  filename(raw) {
    const parts = tileParts(raw);
    if (!parts) throw new Error("Invalid tile URL");
    return path.join(this.directory,parts.join("_")+".json");
  }
  get(raw,now=Date.now()) {
    const file = this.filename(raw);
    if (!fs.existsSync(file)) return null;
    if (fs.lstatSync(file).isSymbolicLink()) throw new Error("Invalid tile cache file");
    const value = JSON.parse(fs.readFileSync(file,"utf8"));
    if (value.url!==raw || !Number.isFinite(value.expires) || value.expires<=now) return null;
    const body = Buffer.from(value.body,"base64");
    if (body.length>1048576 || !body.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))
      throw new Error("Invalid tile cache body");
    return {body,headers:{"content-type":"image/png",
      "cache-control":`public, max-age=${Math.floor((value.expires-now)/1000)}`}};
  }
  put(raw,headers,body,now=Date.now()) {
    const file = this.filename(raw);
    const control = headers["cache-control"] || "";
    if (body.length>1048576 ||
        !body.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))
      throw new Error("Invalid tile response");
    if (/no-store|no-cache/i.test(control)) return false;
    const age = /(?:^|,)\s*max-age=(\d+)/i.exec(control);
    const date = Date.parse(headers.date);
    const serverExpiry = Date.parse(headers.expires);
    const currentAge = Math.max(Number(headers.age||0)*1000,Number.isFinite(date)?Math.max(0,now-date):0);
    const lifetime = age ? Number(age[1])*1000 :
      (Number.isFinite(serverExpiry) ? serverExpiry-(Number.isFinite(date)?date:now) : 7*86400000);
    const ttl = lifetime-currentAge;
    if (!Number.isFinite(ttl) || ttl<=0) return false;
    if (fs.existsSync(file) && fs.lstatSync(file).isSymbolicLink()) throw new Error("Invalid tile cache file");
    if (!fs.existsSync(file) && fs.readdirSync(this.directory).length>=128) throw new Error("Tile cache capacity");
    fs.writeFileSync(file,JSON.stringify({url:raw,expires:now+ttl,cache_control:control||"max-age=604800",
      body:body.toString("base64")}),{mode:0o600});
  }
}

class TileGuard {
  constructor(start = Date.now()) {
    this.start = start; this.attempts = 0; this.sent = 0;
    this.next = start; this.seen = new Set(); this.queue = Promise.resolve(); this.lastSend = -Infinity;
    this.stopped = false;
    this.refusals = {invalid_url:0,duplicate:0,capacity:0,deadline:0,stopped:0};
  }
  refusalStats() { return {...this.refusals}; }
  send(callback) {
    // Serialize actual starts too: delayed timers must not bunch after a stall.
    const next = this.queue.then(async()=>{
      if (this.stopped) throw new Error("Tile provider stopped");
      await new Promise(resolve=>setTimeout(resolve,Math.max(0,this.lastSend+1000-Date.now())));
      if (this.stopped || Date.now()-this.start>90000) throw new Error("Tile deadline");
      this.lastSend = Date.now(); ++this.sent;
      return callback();
    });
    this.queue = next.catch(()=>{});
    return next;
  }
  claim(raw, now = Date.now()) {
    if (this.stopped) { ++this.refusals.stopped; return null; }
    if (!tileParts(raw)) { ++this.refusals.invalid_url; return null; }
    if (this.seen.has(raw)) { ++this.refusals.duplicate; return null; }
    if (this.attempts >= 60) { ++this.refusals.capacity; return null; }
    if (now - this.start > 90000) { ++this.refusals.deadline; return null; }
    const scheduled = Math.max(now, this.next);
    if (scheduled - this.start > 90000) { ++this.refusals.deadline; return null; }
    ++this.attempts; this.seen.add(raw); this.next = scheduled + 1000;
    return scheduled - now;
  }
}

class BackendGuard {
  constructor(listingId) { this.listingId=listingId; this.modes=new Set(); this.nearby=0; }
  claim(raw,method,body) {
    const u = new URL(raw);
    if (u.origin!=="http://127.0.0.1:3033" || u.search) return false;
    if (method!=="POST") return method==="GET";
    if (!body || body.listing_id!==this.listingId) return false;
    if (u.pathname==="/api/mobility/routes" && body.campus_id==="khu_ii" &&
        ["WALK","BICYCLE"].includes(body.requested_mode) && !this.modes.has(body.requested_mode)) {
      this.modes.add(body.requested_mode); return true;
    }
    if (u.pathname==="/api/mobility/nearby" && body.radius_m===1000 &&
        JSON.stringify(body.categories)==='["pharmacy"]' && this.nearby===0) {
      ++this.nearby; return true;
    }
    return false;
  }
}

async function run(listingId, screenshot) {
  const root = path.resolve(__dirname,"..");
  const runtime = "D:\\Dev\\Data\\NCKH\\mobility-catalog-acceptance-20261004-01";
  if (!Number.isSafeInteger(listingId) || listingId < 1 ||
      path.dirname(path.resolve(screenshot)) !== runtime || fs.existsSync(screenshot))
    throw new Error("Invalid pilot target");
  const {chromium, expect} = require(path.join(root,"apps/web/node_modules/@playwright/test"));
  // Visible, single interactive view; no synthetic pan/zoom or catalog sweep.
  const browser = await chromium.launch({headless:false});
  const guard = new TileGuard();
  const backend = new BackendGuard(listingId);
  const cache = new TileCache(path.join(runtime,"P5_TILE_CACHE"));
  const report = {status:"NOT_VERIFIED", routes:[], nearby:null, tiles:null};
  let loaded = 0, failed = 0, cacheHits = 0;
  const failures = {http:{},transport:0,cache:0,fulfill:0,budget:0,deadline:0,lifecycle:0};
  const lifecycleBreakdown = {after_closing:0,handler_rejected:0,initial_drain_timeout:0,
    browser_close_error:0,post_close_drain_timeout:0};
  const zoomHistogram = {};
  const activeRoutes = new Set();
  let step="launch", page, context, closing=false, sealed=false, routePass=true, nearbyPass=false, tilesPass=false;
  try {
    context = await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:"block"});
    const handleRoute = async route => {
      if (closing || sealed) {
        ++failed; ++failures.lifecycle; ++lifecycleBreakdown.after_closing;
        return route.abort().catch(()=>{});
      }
      const u = new URL(route.request().url());
      if (u.origin === "http://127.0.0.1:3033") {
        if (route.request().method()==="POST") {
          let body;
          try { body=route.request().postDataJSON(); } catch { return route.abort(); }
          return backend.claim(u.href,"POST",body) ? route.continue() : route.abort();
        }
        return route.request().method()==="GET" ? route.continue() : route.abort();
      }
      if (!tileParts(u.href)) return route.abort();
      try {
        const cached = cache.get(u.href);
        if (cached) { await route.fulfill({status:200,...cached}); ++cacheHits; return; }
      } catch { ++failed; ++failures.cache; return route.abort().catch(()=>{}); }
      const delay = guard.claim(u.href);
      if (delay === null) { ++failed; ++failures.budget; return route.abort(); }
      const zoom = tileParts(u.href)[0];
      zoomHistogram[zoom]=(zoomHistogram[zoom]||0)+1;
      let phase="transport";
      try {
        await new Promise(resolve=>setTimeout(resolve,delay));
        if (sealed) return route.abort().catch(()=>{});
        if (Date.now() - guard.start > 90000) {
          ++failed; ++failures.deadline; guard.stopped=true; return route.abort();
        }
        const response = await guard.send(()=>route.fetch({maxRedirects:0,maxRetries:0,timeout:10000,
          headers:{"User-Agent":"NCKH-Tro-CTU/0.1 (+https://github.com/nhuy2005-alexandors)",
            "Referer":"http://127.0.0.1:3033/map", "Accept":"image/png"}}));
        const bytes = await response.body();
        if (sealed) return route.abort().catch(()=>{});
        if (response.status() !== 200 || !response.headers()["content-type"]?.startsWith("image/png") ||
            bytes.length > 1048576) {
          ++failed; failures.http[response.status()]=(failures.http[response.status()]||0)+1;
          guard.stopped=true; return route.abort();
        }
        phase="cache";
        const cached = cache.put(u.href,response.headers(),bytes);
        if (cached === false) failures.uncacheable=(failures.uncacheable||0)+1;
        phase="fulfill";
        await route.fulfill({response,body:bytes});
        ++loaded;
      } catch { ++failed; ++failures[phase]; await route.abort().catch(()=>{}); }
    };
    await context.route("**/*", route => {
      // Register the whole invocation before running any async branch. Keep this
      // interceptor installed: unrouteAll(wait) would let new requests escape.
      const task = Promise.resolve().then(()=>handleRoute(route)).catch(()=>{
        ++failed; ++failures.lifecycle; ++lifecycleBreakdown.handler_rejected;
      });
      activeRoutes.add(task);
      return task.finally(()=>activeRoutes.delete(task));
    });
    page = await context.newPage();
    page.setDefaultTimeout(20000);
    step="catalog";
    await page.goto("http://127.0.0.1:3033/map",{waitUntil:"domcontentloaded"});
    await expect(page.getByTestId("catalog-count")).toContainText("789");
    const visibleTilesLoaded = ()=>{
      const tiles=[...document.querySelectorAll(".leaflet-tile")];
      return tiles.length>0 && tiles.every(i=>i.complete && i.naturalWidth>0);
    };
    step="initial_tiles";
    try { await page.waitForFunction(visibleTilesLoaded,{},{timeout:30000}); report.initial_tiles=true; }
    catch { report.initial_tiles=false; }
    step="selection";
    await page.locator(`[data-listing-id="${listingId}"]`).click();
    await page.getByLabel("Khuôn viên",{exact:true}).selectOption("khu_ii");
    for (const mode of ["WALK","BICYCLE"]) {
      step=`route_${mode}`;
      await page.getByLabel("Phương tiện",{exact:true}).selectOption(mode);
      const wait = page.waitForResponse(r=>r.url().endsWith("/api/mobility/routes") && r.request().method()==="POST");
      await page.getByRole("button",{name:"Tính tuyến tới khu đã chọn",exact:true}).click();
      const r = await wait; const v = await r.json();
      report.routes.push({mode,status:v.status,provider:v.provider,evidence_kind:v.evidence_kind,
        observed_at:v.observed_at,duration_seconds:v.duration_seconds,distance_meters:v.distance_meters,
        geometry_points:v.polyline?.length || 0});
      if (r.status() !== 200 || v.status !== "OK" || v.evidence_kind !== "LIVE" ||
          v.provider !== "ors" || v.effective_mode !== mode || !v.observed_at || !v.polyline?.length) {
        routePass=false;
      } else {
        await expect(page.getByTestId("route-result-khu_ii")).toHaveAttribute("data-status","OK");
        await expect(page.locator('path[data-route-source="LIVE"][data-route-provider="ors"]')).toBeVisible();
      }
    }
    step="nearby";
    await page.getByLabel("Bán kính tiện ích",{exact:true}).selectOption("1000");
    await page.getByLabel("Danh mục tiện ích",{exact:true}).selectOption(["pharmacy"]);
    const wait = page.waitForResponse(r=>r.url().endsWith("/api/mobility/nearby") && r.request().method()==="POST");
    await page.getByRole("button",{name:"Tìm tiện ích quanh tin",exact:true}).click();
    const near = await wait; const v = await near.json();
    report.nearby = {status:v.status,provider:v.provider,evidence_kind:v.evidence_kind,
      queried_at:v.queried_at,coverage:v.coverage,item_count:v.items?.length || 0};
    nearbyPass=near.status()===200 && ["OK","EMPTY"].includes(v.status) &&
        v.provider==="osm_overpass" && v.evidence_kind==="LIVE" && Boolean(v.queried_at);
    if (nearbyPass) await expect(page.getByTestId("nearby-result")).toHaveAttribute("data-status",v.status);
    if (nearbyPass && v.status==="OK") {
      await expect(page.locator('[data-nearby-source="LIVE"]')).toHaveCount(v.items.length);
    }
    step="final_tiles";
    try { await page.waitForFunction(visibleTilesLoaded,{},{timeout:35000}); tilesPass=true; }
    catch { tilesPass=false; }
    await expect(page.getByTestId("map-attribution")).toContainText("OpenStreetMap");
    await page.screenshot({path:screenshot,fullPage:true});
    report.status=routePass && nearbyPass && tilesPass && (loaded+cacheHits)>0 && failed===0 && guard.sent<=60 ? "PASS" : "NOT_VERIFIED";
    report.capabilities={routes:routePass,nearby:nearbyPass,tiles:tilesPass && failed===0};
    step="complete";
  } catch (error) {
    report.error_type = error.name;
  } finally {
    report.step=step;
    if (page && !fs.existsSync(screenshot)) await page.screenshot({path:screenshot,fullPage:true}).catch(()=>{});
    // Freeze admission, without unregistering the allowlist, and wait for every
    // invocation (including cache paths and pre-send timers) to settle.
    // Claims expire at 90s and fetches at 10s; shutdown never waits indefinitely.
    closing=true;
    const drained = await drainRoutes(activeRoutes,guard.start+100000);
    sealed=true;
    if (!drained) {
      ++failed; ++failures.lifecycle; ++lifecycleBreakdown.initial_drain_timeout;
      guard.stopped=true;
    }
    try { await browser.close(); }
    catch { ++failed; ++failures.lifecycle; ++lifecycleBreakdown.browser_close_error; }
    const closeDrained = await drainRoutes(activeRoutes,Date.now()+2000);
    if (!closeDrained) {
      ++failed; ++failures.lifecycle; ++lifecycleBreakdown.post_close_drain_timeout;
    }
    if (failed || guard.stopped) {
      report.status="NOT_VERIFIED";
      if (report.capabilities) report.capabilities.tiles=false;
    }
    // Detached data also stays stable if a timed-out driver callback rejects late.
    report.tiles=JSON.parse(JSON.stringify({claimed:guard.attempts,sent:guard.sent,loaded,failed,
      cache_hits:cacheHits,failures,lifecycle_breakdown:lifecycleBreakdown,
      claim_refusals:guard.refusalStats(),zoom_histogram:zoomHistogram,
      handlers_drained:drained && closeDrained}));
  }
  return report;
}

module.exports = {TileGuard,TileCache,BackendGuard};
if (require.main === module) {
  run(Number(process.argv[2]),process.argv[3]).then(r=>{
    console.log(JSON.stringify(r)); process.exitCode = r.status === "PASS" ? 0 : 1;
  }).catch(e=>{console.log(JSON.stringify({status:"NOT_VERIFIED",error_type:e.name}));process.exitCode=1;});
}
