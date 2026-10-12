"""Pure Node tile guard, no browser/network."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_tile_guard_atomic_budget_spacing_deadline_and_origin():
    root = Path(__file__).resolve().parents[3]
    script = r'''
const assert = require('node:assert/strict');
const {TileGuard,BackendGuard} = require('./scripts/open_mobility_tile_pilot.cjs');
const g = new TileGuard(0);
const urls = Array.from({length:61}, (_,i)=>`https://tile.openstreetmap.org/12/${i}/3.png`);
const claims = urls.map(u=>g.claim(u,0));
assert.equal(claims.filter(x=>x!==null).length,60);
assert.equal(g.attempts,60);
assert.equal(claims[1],1000);
assert.equal(claims[59],59000);
for(const u of ['https://wrong.test/12/3/4.png','http://tile.openstreetmap.org/12/3/4.png',
 'https://tile.openstreetmap.org/12/3/4.png?key=x','https://tile.openstreetmap.org/a.png',
 'https://tile.openstreetmap.org/12/4096/4.png']) {
 assert.equal(new TileGuard(0).claim(u,0),null);
}
assert.equal(new TileGuard(0).claim(urls[0],90001),null);
const repeat = new TileGuard(0);
assert.equal(repeat.claim(urls[0],0),0);
assert.equal(repeat.claim(urls[0],0),null);
const stopped = new TileGuard(0);
stopped.stopped = true;
assert.equal(stopped.claim(urls[0],0),null);
const backend=new BackendGuard(123);
const route='http://127.0.0.1:3033/api/mobility/routes';
const body={listing_id:123,campus_id:'khu_ii',requested_mode:'WALK'};
assert.equal(backend.claim(route,'POST',body),true);
assert.equal(backend.claim(route,'POST',body),false);
assert.equal(backend.claim(route,'POST',{...body,requested_mode:'MOTORBIKE'}),false);
assert.equal(backend.claim(route,'POST',{...body,listing_id:99,requested_mode:'BICYCLE'}),false);
assert.equal(backend.claim(route,'POST',{...body,requested_mode:'BICYCLE'}),true);
const near='http://127.0.0.1:3033/api/mobility/nearby';
const query={listing_id:123,radius_m:1000,categories:['pharmacy']};
assert.equal(backend.claim(near,'POST',query),true);
assert.equal(backend.claim(near,'POST',query),false);
console.log('TILE_GUARD_PASS');
'''
    result = subprocess.run([shutil.which("node"), "-e", script], cwd=root,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "TILE_GUARD_PASS"


def test_tile_guard_refusal_diagnostics_are_allowlisted_and_defensive():
    root = Path(__file__).resolve().parents[3]
    script = r'''
const assert = require('node:assert/strict');
const {TileGuard} = require('./scripts/open_mobility_tile_pilot.cjs');
const url = i => `https://tile.openstreetmap.org/12/${i}/3.png`;
const g = new TileGuard(0);
assert.equal(g.claim('https://wrong.test/not-a-tile', 0), null);
assert.equal(g.claim(url(0), 0), 0);
assert.equal(g.claim(url(0), 0), null);
for (let i = 1; i < 60; i++) g.claim(url(i), 0);
assert.equal(g.claim(url(60), 0), null);
const stopped = new TileGuard(0); stopped.stopped = true;
assert.equal(stopped.claim(url(0), 0), null);
const deadline = new TileGuard(0);
assert.equal(deadline.claim(url(0), 90001), null);
const stats = g.refusalStats();
assert.deepEqual(stats, {invalid_url: 1, duplicate: 1, capacity: 1, deadline: 0, stopped: 0});
stats.capacity = 99;
assert.equal(g.refusalStats().capacity, 1);
assert.deepEqual(stopped.refusalStats(), {invalid_url: 0, duplicate: 0, capacity: 0, deadline: 0, stopped: 1});
assert.deepEqual(deadline.refusalStats(), {invalid_url: 0, duplicate: 0, capacity: 0, deadline: 1, stopped: 0});
console.log('TILE_REFUSAL_DIAGNOSTICS_PASS');
'''
    result = subprocess.run([shutil.which("node"), "-e", script], cwd=root,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "TILE_REFUSAL_DIAGNOSTICS_PASS"


def test_tile_cache_honors_server_ttl_and_rejects_invalid_targets_and_nocache(tmp_path):
    root = Path(__file__).resolve().parents[3]
    script = r'''
const assert = require('node:assert/strict');
const {TileCache} = require('./scripts/open_mobility_tile_pilot.cjs');
const cache = new TileCache(process.argv[1]);
const u = 'https://tile.openstreetmap.org/12/3/4.png';
const body = Buffer.from([137,80,78,71,13,10,26,10]);
cache.put(u,{'cache-control':'public, max-age=60',age:'10'},body,1000);
assert.deepEqual(cache.get(u,50999).body,body);
assert.equal(cache.get(u,51000),null);
assert.equal(cache.put(u,{'cache-control':'no-store'},body),false);
assert.throws(()=>cache.put(u,{'cache-control':'no-store'},Buffer.from('not-png')));
assert.throws(()=>cache.put(u,{'cache-control':'max-age=0'},Buffer.from('not-png')));
assert.throws(()=>cache.get('https://wrong.test/12/3/4.png'));
const v = 'https://tile.openstreetmap.org/12/4/4.png';
cache.put(v,{},body,0);
assert.equal(cache.get(v,7*86400000),null);
const aged = 'https://tile.openstreetmap.org/12/5/4.png';
cache.put(aged,{date:'Thu, 01 Jan 1970 00:00:00 GMT',expires:'Thu, 01 Jan 1970 00:01:00 GMT',age:'50'},body,0);
assert.deepEqual(cache.get(aged,9999).body,body);
assert.equal(cache.get(aged,10000),null);
const oldDate = 'https://tile.openstreetmap.org/12/6/4.png';
cache.put(oldDate,{'cache-control':'max-age=60',date:'Thu, 01 Jan 1970 00:00:00 GMT',age:'0'},body,50000);
assert.deepEqual(cache.get(oldDate,59999).body,body);
assert.equal(cache.get(oldDate,60000),null);
console.log('CACHE_PASS');
'''
    result = subprocess.run([shutil.which("node"), "-e", script, str(tmp_path)],
                            cwd=root, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "CACHE_PASS"


@pytest.mark.parametrize("failure_kind", ["budget", "deadline", "late", "pending", "shutdown_timeout",
                                        "drain_admission", "handler_rejected", "browser_close_error"])
def test_real_pilot_cannot_pass_after_61st_tile_is_aborted_and_removed_from_viewport(failure_kind):
    root = Path(__file__).resolve().parents[3]
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const source=fs.readFileSync('scripts/open_mobility_tile_pilot.cjs','utf8');
let handler,mode='WALK',kind='route',aborted=0;
const failureKind=process.argv[1];let fetched=0,now=0,pending,releaseDelay,closed=false,delayHeld=false,unregistered=false,leaked=0;
const pendingKinds=['pending','shutdown_timeout','drain_admission'];
class FakeDate extends Date {static now(){return now;}}
const png=Buffer.from([137,80,78,71,13,10,26,10]);
const fakeFs={mkdirSync(){},lstatSync:()=>({isSymbolicLink:()=>false}),existsSync:()=>false,
 readdirSync:()=>[],writeFileSync(){}};
const assertion={toContainText:async()=>{},toHaveAttribute:async()=>{},toBeVisible:async()=>{},toHaveCount:async()=>{}};
const page={setDefaultTimeout(){},async goto(){
 for(let x=0;x<(failureKind==='deadline'?2:pendingKinds.includes(failureKind)?1:
  ['late','handler_rejected','browser_close_error'].includes(failureKind)?60:61);x++) await handler({
  request:()=>({url:()=>`https://tile.openstreetmap.org/12/${x}/3.png`}),
  abort:async()=>{++aborted;},fetch:async()=>{++fetched;return {status:()=>200,
   headers:()=>({'content-type':'image/png','cache-control':'max-age=60'}),body:async()=>png};},fulfill:async()=>{}});
 if(pendingKinds.includes(failureKind))pending=handler({
  request:()=>({url:()=>`https://tile.openstreetmap.org/12/1/3.png`}),abort:async()=>{++aborted;},
  fetch:async()=>{throw new Error('Target closed');},fulfill:async()=>{}});
 if(failureKind==='handler_rejected')await handler({request:()=>{throw new Error('private handler sentinel');}});
 },getByTestId:()=>({}),locator:()=>({click:async()=>{}}),
 getByLabel:label=>({selectOption:async v=>{if(label==='Phương tiện')mode=v;}}),
 getByRole:(_role,opt)=>({click:async()=>{kind=opt.name.startsWith('Tìm')?'nearby':'route';}}),
 waitForResponse:()=>Promise.resolve({status:()=>200,json:async()=>kind==='nearby'?
  {status:'EMPTY',provider:'osm_overpass',evidence_kind:'LIVE',queried_at:'2026-10-11T00:00:00Z',items:[]}:
  {status:'OK',provider:'ors',evidence_kind:'LIVE',effective_mode:mode,observed_at:'2026-10-11T00:00:00Z',polyline:[{},{}]}}),
 waitForFunction:async()=>{},screenshot:async()=>{if(failureKind==='shutdown_timeout')now=99999;}};
const browser={newContext:async()=>({route:async(_,cb)=>{handler=cb;},newPage:async()=>page,
 unrouteAll:()=>{unregistered=true;if(failureKind==='drain_admission')++leaked;
  if(failureKind==='shutdown_timeout'){now=99999;return new Promise(()=>{});}
  if(releaseDelay)releaseDelay();return pending||Promise.resolve();}}),close:async()=>{
 closed=true;
 if(failureKind==='browser_close_error')throw new Error('private close sentinel');
 if(failureKind==='late')await handler({request:()=>({url:()=>`https://tile.openstreetmap.org/12/60/3.png`}),abort:async()=>{++aborted;}});
}};
const sandbox={require:name=>name==='node:path'?path.win32:name==='node:fs'?fakeFs:name==='node:timers'?require(name):
 {chromium:{launch:async()=>browser},expect:()=>assertion},__dirname:'D:\\Dev\\Workspaces\\NCKH\\scripts',
 module:{exports:{}},process:{argv:[]},Buffer,URL,Date:FakeDate,clearTimeout(){},setTimeout:(cb,delay)=>{
  if(pendingKinds.includes(failureKind) && fetched>0 && delay>0 && !delayHeld){
   delayHeld=true;releaseDelay=cb;
   if(failureKind!=='shutdown_timeout')require('node:timers').setTimeout(async()=>{
    if(failureKind==='drain_admission' && !unregistered)await handler({
     request:()=>({url:()=>`https://blocked.test/not-approved`}),abort:async()=>{++aborted;}});
    cb();},5);
   return 1;}
  if(failureKind==='deadline' && fetched>0)now=90001;cb();return 1;}};
vm.runInNewContext(source+'\nmodule.exports.run=run;',sandbox);
sandbox.module.exports.run(123,'D:\\Dev\\Data\\NCKH\\mobility-catalog-acceptance-20261004-01\\synthetic-probe.png').then(async r=>{
 assert.equal(leaked,0,'interceptor must stay registered throughout drain');
 assert.equal(aborted,['shutdown_timeout','handler_rejected','browser_close_error'].includes(failureKind)?0:
  failureKind==='drain_admission'?2:1);
 assert.equal(r.tiles.loaded,['deadline',...pendingKinds].includes(failureKind)?1:60);
 assert.equal(r.tiles.failures[failureKind==='deadline'?'deadline':['pending','drain_admission'].includes(failureKind)?
  'transport':['late','shutdown_timeout','handler_rejected','browser_close_error'].includes(failureKind)?'lifecycle':'budget'],
  failureKind==='shutdown_timeout'?2:1);
 assert.equal(r.status,'NOT_VERIFIED');assert.equal(r.capabilities.tiles,false);
 assert.equal(r.tiles.failed,['drain_admission','shutdown_timeout'].includes(failureKind)?2:1);
 const lifecycle = r.tiles.lifecycle_breakdown;
 assert.ok(lifecycle, 'private lifecycle breakdown must survive the final receipt');
 const expectedLifecycle = {after_closing:0,handler_rejected:0,initial_drain_timeout:0,
  browser_close_error:0,post_close_drain_timeout:0};
 if(failureKind==='late' || failureKind==='drain_admission')expectedLifecycle.after_closing=1;
 if(failureKind==='handler_rejected')expectedLifecycle.handler_rejected=1;
 if(failureKind==='browser_close_error')expectedLifecycle.browser_close_error=1;
 if(failureKind==='shutdown_timeout'){
  expectedLifecycle.initial_drain_timeout=1;
  expectedLifecycle.post_close_drain_timeout=1;
 }
 assert.deepEqual(JSON.parse(JSON.stringify(lifecycle)),expectedLifecycle);
 assert.equal(Object.values(lifecycle).reduce((a,b)=>a+b,0),r.tiles.failures.lifecycle);
 assert.equal(r.tiles.claim_refusals.capacity,failureKind==='budget'?1:0);
 assert.equal(JSON.stringify(r).includes('private'),false);
 if(['pending','shutdown_timeout'].includes(failureKind)){
  assert.equal(closed,true);const snapshot=JSON.stringify(r);
  if(releaseDelay)releaseDelay();await pending;
  assert.equal(JSON.stringify(r),snapshot);
  assert.equal(r.tiles.handlers_drained,failureKind==='pending');
 }
 console.log('SYNTHETIC_RUN_BUDGET_GUARD_PASS');
}).catch(e=>{console.error(e.name,e.message);process.exitCode=1;});
'''
    result = subprocess.run([shutil.which("node"), "-e", script, failure_kind], cwd=root,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "SYNTHETIC_RUN_BUDGET_GUARD_PASS"
