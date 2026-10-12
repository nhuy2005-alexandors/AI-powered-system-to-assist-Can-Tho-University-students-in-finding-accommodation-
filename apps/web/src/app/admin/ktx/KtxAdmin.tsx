"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import type { KtxCatalog, KtxRoomType, KtxPhysicalRoom } from "@/lib/ktx";

type Year = { id: number; academic_year: string; revision: number; is_active: boolean; archived: boolean;
  has_changes: boolean; room_types: number; rooms: number; images: number; published_at: string | null };
type Detail = Year & { catalog: KtxCatalog; audit?: { id: number; action: string; actor_name: string | null; created_at: string }[] };
const input = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm disabled:bg-slate-100";
const button = "rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50";
const coreFacts = new Set(["fees", "utilities", "parking", "wifi", "security", "quiet", "registration", "availability", "contact"]);
const tabs = [["general", "Thông tin chung"], ["areas", "Khu & vị trí"], ["types", "Loại phòng"], ["rooms", "Từng phòng"], ["images", "Hình ảnh"], ["facts", "Thông tin tư vấn"], ["sources", "Nguồn dữ liệu"], ["audit", "Lịch sử"]];
const uid = () => crypto.randomUUID();

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block space-y-1.5 text-sm font-medium text-slate-700"><span>{label}</span>{children}</label>;
}
function Text({ label, value, onChange, multiline = false, type = "text" }: { label: string; value: string | number;
  onChange: (value: string) => void; multiline?: boolean; type?: string }) {
  return <Field label={label}>{multiline ? <textarea className={input} rows={3} value={value} onChange={e => onChange(e.target.value)} />
    : <input className={input} type={type} value={value} onChange={e => onChange(e.target.value)} />}</Field>;
}
function errorText(detail: unknown): string {
  if (Array.isArray(detail)) return detail.map(item => `${(item.loc || []).slice(1).join(" / ")}: ${item.msg}`).join("; ");
  return typeof detail === "string" ? detail : "Không xử lý được yêu cầu";
}
async function api<T>(path: string, method = "GET", data?: unknown): Promise<T> {
  const form = data instanceof FormData;
  const response = await fetch("/api/admin/ktx/" + path, { method, cache: "no-store",
    headers: data && !form ? { "Content-Type": "application/json" } : undefined,
    body: data ? (form ? data : JSON.stringify(data)) : undefined });
  const result = await response.json();
  if (!response.ok) throw new Error(errorText(result.detail));
  return result;
}

export default function KtxAdmin() {
  const [years, setYears] = useState<Year[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [draft, setDraft] = useState<KtxCatalog | null>(null);
  const [tab, setTab] = useState("general");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [newYear, setNewYear] = useState(`${new Date().getFullYear()}-${new Date().getFullYear() + 1}`);
  const [typeId, setTypeId] = useState("");
  const [roomId, setRoomId] = useState("");
  const [search, setSearch] = useState("");

  async function load(id?: number) {
    const list = await api<{ items: Year[] }>("years");
    setYears(list.items);
    const selected = id || list.items.find(item => item.is_active)?.id || list.items[0]?.id;
    if (selected) {
      const data = await api<Detail>(`years/${selected}`);
      setDetail(data); setDraft(data.catalog); setDirty(false);
      setTypeId(data.catalog.room_types[0]?.id || ""); setRoomId(data.catalog.rooms?.[0]?.id || "");
    }
  }
  useEffect(() => { setBusy(true); load().catch(e => setError(e.message)).finally(() => setBusy(false)); }, []);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  async function action(fn: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await fn(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  function change(next: KtxCatalog) { setDraft(next); setDirty(true); setMessage(""); }
  function updateType(patch: Partial<KtxRoomType>) {
    if (draft) change({ ...draft, room_types: draft.room_types.map(item => item.id === typeId ? { ...item, ...patch } : item) });
  }
  function updateRoom(patch: Partial<KtxPhysicalRoom>) {
    if (draft) change({ ...draft, rooms: (draft.rooms || []).map(item => item.id === roomId ? { ...item, ...patch } : item) });
  }
  async function save(): Promise<Detail> {
    if (!detail || !draft) throw new Error("Chưa chọn năm học");
    const data = await api<Detail>(`years/${detail.id}`, "PUT", { revision: detail.revision, catalog: draft });
    const fresh = await api<Detail>(`years/${detail.id}`);
    setDetail(fresh); setDraft(fresh.catalog); setDirty(false); return fresh;
  }
  const type = draft?.room_types.find(item => item.id === typeId);
  const room = draft?.rooms?.find(item => item.id === roomId);
  const locked = busy || !!detail?.archived;

  return <div className="mx-auto max-w-7xl space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-3xl font-bold">Quản lý ký túc xá</h1>
      <p className="mt-2 text-sm text-slate-600">Lưu bản nháp theo năm học; công bố để cập nhật trang KTX, bản đồ và trợ lý AI.</p></div>
      <Link href="/ktx" className={button} target="_blank">Xem trang KTX ↗</Link></div>
    {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</p>}
    {message && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{message}</p>}
    <section className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 md:grid-cols-2">
      <Field label="Năm học đang chỉnh sửa"><select disabled={busy} className={input} value={detail?.id || ""} onChange={e => {
        if (dirty && !confirm("Bỏ thay đổi chưa lưu để chuyển năm học?")) return;
        action(() => load(Number(e.target.value)));
      }}><option value="" disabled>Chọn năm học</option>{years.map(y => <option key={y.id} value={y.id}>{y.academic_year}{y.is_active ? " · đang công bố" : ""}{y.archived ? " · lưu trữ" : y.has_changes ? " · có bản nháp" : ""}</option>)}</select></Field>
      <div className="flex items-end gap-2"><div className="min-w-0 flex-1"><Text label="Tạo năm học mới (sao chép năm đang chọn)" value={newYear} onChange={setNewYear} /></div><button disabled={busy} className={button} onClick={() => action(async () => {
        if (dirty && !confirm("Năm mới sẽ sao chép bản nháp đã lưu. Tiếp tục?")) return;
        const data = await api<Detail>("years", "POST", { academic_year: newYear, copy_from: detail?.id || null });
        await load(data.id); setMessage("Đã tạo bản nháp năm học. Rà lại giá, nguồn và ngày ghi nhận trước khi công bố.");
      })}>Tạo năm</button></div>
    </section>
    {detail && draft && <>
      <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-sm lg:top-20">
        <p className="text-sm"><strong>{detail.academic_year}</strong> · {draft.room_types.length} loại phòng · {(draft.rooms || []).length} phòng · {draft.images.length} ảnh
          <span className="ml-2 text-amber-700">{dirty ? "Chưa lưu" : detail.has_changes ? "Bản nháp đã lưu" : detail.is_active ? "Đang công bố" : "Đã lưu"}</span></p>
        <div className="flex flex-wrap gap-2"><button disabled={locked || !dirty} className={button} onClick={() => action(async () => { await save(); setMessage("Đã lưu bản nháp. Trang KTX và chatbot vẫn dùng bản đã công bố."); })}>Lưu bản nháp</button>
          <button disabled={locked} className={button + " !border-emerald-600 !bg-emerald-600 !text-white"} onClick={() => action(async () => {
            const saved = dirty ? await save() : detail;
            setMessage("Đang cập nhật dữ liệu chatbot và công bố…");
            await api(`years/${saved.id}/publish`, "POST", { revision: saved.revision }); await load(saved.id);
            setMessage("Đã công bố. Trang KTX, bản đồ và chatbot cùng dùng năm học này.");
          })}>{busy ? "Đang xử lý…" : "Công bố & dùng năm này"}</button>
          {!detail.is_active && <button disabled={busy || dirty} className={button} onClick={() => action(async () => {
            await api(`years/${detail.id}/archive`, "POST", { revision: detail.revision }); await load(detail.id);
          })}>{detail.archived ? "Khôi phục" : "Lưu trữ năm"}</button>}
          <button disabled={busy} className={button} onClick={() => { if (!dirty || confirm("Bỏ thay đổi chưa lưu?")) action(() => load(detail.id)); }}>Tải lại</button></div>
      </div>
      <nav className="flex gap-2 overflow-x-auto" aria-label="Các mục quản lý KTX">{tabs.map(([id, label]) => <button key={id} type="button" onClick={() => {setTab(id);setSearch("");}} className={button + " shrink-0 " + (tab === id ? "!border-blue-700 !bg-blue-700 !text-white" : "")}>{label}</button>)}</nav>
      <fieldset disabled={locked} className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        {tab === "general" && <div className="grid gap-4 md:grid-cols-2"><Text label="Học kỳ / tên đợt" value={draft.term || ""} onChange={term => change({...draft,term})} />
          <Text label="Email liên hệ" value={draft.email} onChange={email => change({...draft,email})} type="email" />
          <Text label="Địa chỉ" value={draft.address} onChange={address => change({...draft,address})} />
          <Text label="Trang đăng ký chính thức" value={draft.registration_url} onChange={registration_url => change({...draft,registration_url})} />
          <p className="text-sm text-slate-500 md:col-span-2">Năm học là nhãn quản lý danh mục. Giá và nội quy chỉ áp dụng theo nguồn đã xác nhận; sao chép năm không tự xác nhận giá mới.</p></div>}
        {tab === "areas" && <div className="space-y-8">{draft.dormitories.map((area,index) => {
          const update = (patch: Partial<typeof area>) => change({...draft,dormitories:draft.dormitories.map((item,i) => i === index ? {...item,...patch} : item)});
          return <section key={area.id} className="space-y-4"><h2 className="text-lg font-bold">Khu {area.id}</h2><div className="grid gap-4 md:grid-cols-2">
            <Text label="Tên khu" value={area.name} onChange={name => update({name})} /><Text label="Điện thoại" value={area.phone} onChange={phone => update({phone})} />
            <Text label="Sức chứa toàn khu" value={area.capacity} type="number" onChange={v => update({capacity:Number(v)})} /><Text label="Các dãy nhà" value={area.buildings} onChange={buildings => update({buildings})} />
            <Text label="Giới thiệu" value={area.description} multiline onChange={description => update({description})} />
            <Field label="Ảnh bìa"><select className={input} value={area.cover} onChange={e => update({cover:e.target.value})}>
              <option value={area.cover}>Ảnh đang chọn</option>{draft.images.filter(i => i.dormitory_id === area.id).map(i => <option key={i.src} value={i.src}>{i.alt}</option>)}</select></Field>
            <Text label="Vĩ độ" value={area.location.lat} type="number" onChange={v => update({location:{...area.location,lat:Number(v)}})} />
            <Text label="Kinh độ" value={area.location.lng} type="number" onChange={v => update({location:{...area.location,lng:Number(v)}})} />
            <Text label="Tên điểm đại diện" value={area.location.label} onChange={label => update({location:{...area.location,label}})} />
            <Text label="Nguồn tọa độ" value={area.location.source_url} onChange={source_url => update({location:{...area.location,source_url}})} /></div></section>;
        })}</div>}
        {tab === "types" && <div className="space-y-5"><div className="flex flex-wrap gap-3"><input className={input + " max-w-sm"} aria-label="Tìm loại phòng" placeholder="Tìm mã hoặc mô tả…" value={search} onChange={e => setSearch(e.target.value)} />
          <button className={button} onClick={() => { const item: KtxRoomType = {id:"roomtype-"+uid(),code:"MỚI",area_ids:[],capacities:[4],capacity_label:"4 người",cooking_allowed:null,bed_type:"unknown",bathroom:null,description:"",price:1,price_period:"unconfirmed",source_id:"submitted",notes:""}; change({...draft,room_types:[...draft.room_types,item]});setTypeId(item.id); }}>+ Thêm loại phòng</button></div>
          <div className="grid gap-5 lg:grid-cols-[280px_1fr]"><div className="max-h-[580px] space-y-1 overflow-y-auto rounded-xl border p-2">{draft.room_types.filter(r => (r.code+" "+r.description).toLowerCase().includes(search.toLowerCase())).map(r => <button key={r.id} className={"block w-full rounded-lg p-3 text-left text-sm " + (typeId === r.id ? "bg-blue-50 font-bold text-blue-800" : "hover:bg-slate-50")} onClick={() => setTypeId(r.id)}>{r.code}<span className="block text-xs font-normal text-slate-500">{r.capacity_label} · {r.price.toLocaleString("vi-VN")} đ</span></button>)}</div>
          {type && <div className="grid content-start gap-4 md:grid-cols-2"><Text label="Mã loại phòng" value={type.code} onChange={code => updateType({code})} />
            <Field label="Khu"><select className={input} value={type.area_ids.join(",")} onChange={e => updateType({area_ids:e.target.value ? e.target.value.split(",") as ("A"|"B")[] : []})}><option value="">Chưa xác nhận</option><option value="A">A</option><option value="B">B</option><option value="A,B">A và B</option></select></Field>
            <Field label="Sức chứa (ví dụ 4 hoặc 2,4)"><input key={type.id+type.capacities.join(",")} className={input} defaultValue={type.capacities.join(",")} onBlur={e => { const v=e.target.value; const capacities=v.split(",").map(Number); updateType({capacities,capacity_label:v+" người"}); }} /></Field>
            <Text label="Giá / người (đồng)" type="number" value={type.price} onChange={v => updateType({price:Number(v)})} />
            <Field label="Kỳ tính giá"><select className={input} value={type.price_period} onChange={e => updateType({price_period:e.target.value as KtxRoomType["price_period"]})}><option value="unconfirmed">Chưa xác nhận</option><option value="monthly">Mỗi tháng</option><option value="semester_3_5_months">Học kỳ 3,5 tháng</option></select></Field>
            <Field label="Nấu ăn"><select className={input} value={type.cooking_allowed === null ? "unknown" : String(type.cooking_allowed)} onChange={e => updateType({cooking_allowed:e.target.value === "unknown" ? null : e.target.value === "true"})}><option value="unknown">Chưa xác nhận</option><option value="true">Được nấu ăn</option><option value="false">Không được nấu ăn</option></select></Field>
            <Field label="Giường"><select className={input} value={type.bed_type} onChange={e => updateType({bed_type:e.target.value as KtxRoomType["bed_type"]})}><option value="unknown">Chưa xác nhận</option><option value="single">Giường bộ</option><option value="bunk">Giường tầng</option></select></Field>
            <Text label="Nhà vệ sinh" value={type.bathroom || ""} onChange={v => updateType({bathroom:v || null})} />
            <Text label="Mô tả tiện nghi" value={type.description} multiline onChange={description => updateType({description})} />
            <Text label="Lưu ý giá / thời hạn áp dụng" value={type.notes} multiline onChange={notes => updateType({notes})} />
            <Field label="Nguồn"><select className={input} value={type.source_id} onChange={e => updateType({source_id:e.target.value})}>{draft.sources.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}</select></Field>
            <button className={button + " self-end text-red-700"} onClick={() => { if (confirm("Xóa loại phòng khỏi bản nháp? Cần gỡ phòng và ảnh đang dùng loại này trước khi lưu.")) {change({...draft,room_types:draft.room_types.filter(r => r.id !== type.id)});setTypeId("");} }}>Xóa loại phòng</button></div>}</div></div>}
        {tab === "rooms" && <div className="space-y-5"><div className="flex gap-3"><input className={input + " max-w-sm"} aria-label="Tìm phòng" placeholder="Tìm dãy, số phòng…" value={search} onChange={e => setSearch(e.target.value)} /><button disabled={!draft.room_types.length} className={button} onClick={() => {
          const item:KtxPhysicalRoom={id:"room-"+uid(),dormitory_id:draft.room_types[0].area_ids[0] || "A",building:"",number:"",room_type_id:draft.room_types[0].id,capacity:draft.room_types[0].capacities[0],status:"unknown",available_beds:null,verified_at:null,notes:""};change({...draft,rooms:[...(draft.rooms || []),item]});setRoomId(item.id);
        }}>+ Thêm phòng</button></div>
          <p className="text-sm text-slate-500">Số chỗ là ghi nhận thủ công có ngày xác nhận, không phải tình trạng trực tiếp từ CTU.</p>
          <div className="grid gap-5 lg:grid-cols-[280px_1fr]"><div className="max-h-[560px] space-y-1 overflow-y-auto rounded-xl border p-2">{(draft.rooms || []).filter(r => (r.building+" "+r.number).toLowerCase().includes(search.toLowerCase())).map(r => <button key={r.id} className={"block w-full rounded-lg p-3 text-left text-sm " + (roomId === r.id ? "bg-blue-50 font-bold text-blue-800" : "hover:bg-slate-50")} onClick={() => setRoomId(r.id)}>Khu {r.dormitory_id} · {r.building || "Dãy?"} · {r.number || "Phòng?"}</button>)}{!draft.rooms?.length && <p className="p-3 text-sm text-slate-500">Chưa nhập từng phòng.</p>}</div>
          {room && <div className="grid content-start gap-4 md:grid-cols-2"><Field label="Khu"><select className={input} value={room.dormitory_id} onChange={e => updateRoom({dormitory_id:e.target.value as "A"|"B"})}><option>A</option><option>B</option></select></Field>
            <Text label="Dãy nhà" value={room.building} onChange={building => updateRoom({building})} /><Text label="Số phòng" value={room.number} onChange={number => updateRoom({number})} />
            <Field label="Loại phòng"><select className={input} value={room.room_type_id} onChange={e => {const selected=draft.room_types.find(t=>t.id===e.target.value)!;updateRoom({room_type_id:selected.id,capacity:selected.capacities[0],dormitory_id:selected.area_ids.includes(room.dormitory_id)?room.dormitory_id:selected.area_ids[0] || room.dormitory_id,available_beds:null,status:"unknown",verified_at:null});}}>{draft.room_types.map(t => <option key={t.id} value={t.id}>{t.code}</option>)}</select></Field>
            <Text label="Sức chứa thực tế" type="number" value={room.capacity} onChange={v => updateRoom({capacity:Number(v)})} />
            <Field label="Tình trạng ghi nhận"><select className={input} value={room.status} onChange={e => { const status=e.target.value as KtxPhysicalRoom["status"];updateRoom({status,available_beds:status === "full" || status === "maintenance" ? 0 : null}); }}><option value="unknown">Chưa xác nhận</option><option value="available">Còn chỗ</option><option value="full">Hết chỗ</option><option value="maintenance">Bảo trì</option></select></Field>
            <Text label="Số chỗ trống (để trống nếu chưa biết)" type="number" value={room.available_beds ?? ""} onChange={v => updateRoom({available_beds:v === "" ? null : Number(v)})} />
            <Text label="Ngày ghi nhận" type="date" value={room.verified_at || ""} onChange={v => updateRoom({verified_at:v || null})} />
            <div className="md:col-span-2"><Text label="Ghi chú" multiline value={room.notes} onChange={notes => updateRoom({notes})} /></div>
            <button className={button + " text-red-700"} onClick={() => {if(confirm("Xóa phòng khỏi bản nháp?")){change({...draft,rooms:(draft.rooms || []).filter(r => r.id !== room.id),images:draft.images.map(i => i.room_id === room.id ? {...i,room_id:null} : i)});setRoomId("");}}}>Xóa phòng</button></div>}</div></div>}
        {tab === "images" && <div className="space-y-5"><Field label="Tải ảnh JPG, PNG hoặc WEBP — tối đa 8 MB"><input type="file" accept="image/jpeg,image/png,image/webp" className={input} onChange={e => {
          const file=e.target.files?.[0];if(!file)return;
          if(file.size>8*1024*1024){setError("Ảnh tối đa 8 MB");return;}
          const data=new FormData();data.append("file",file);
          action(async () => {const uploaded=await api<KtxCatalog["images"][number]>("images","POST",data);change({...draft,images:[...draft.images,{...uploaded,alt:file.name.replace(/\.[^.]+$/, ""),dormitory_id:"A",room_id:null,room_type_id:null}]});setMessage("Đã tải ảnh. Chọn khu, chú thích và lưu bản nháp để giữ thay đổi.");});e.target.value="";
        }} /></Field><div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{draft.images.map((image,index) => {
          const update=(patch:Partial<typeof image>) => change({...draft,images:draft.images.map((item,i) => i===index ? {...item,...patch} : item)});
          return <article key={image.src} className="space-y-3 rounded-xl border border-slate-200 p-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}<img src={image.src} alt={image.alt} className="h-40 w-full rounded-lg object-cover" />
            <Text label="Chú thích ảnh" value={image.alt} onChange={alt => update({alt})} />
            <Field label="Khu"><select className={input} value={image.dormitory_id} onChange={e => update({dormitory_id:e.target.value as "A"|"B",room_id:null})}><option>A</option><option>B</option></select></Field>
            <Field label="Gắn với loại phòng"><select className={input} value={image.room_type_id || ""} onChange={e => update({room_type_id:e.target.value || null})}><option value="">Ảnh chung</option>{draft.room_types.map(t => <option key={t.id} value={t.id}>{t.code}</option>)}</select></Field>
            <Field label="Gắn với phòng cụ thể"><select className={input} value={image.room_id || ""} onChange={e => {const linked=draft.rooms?.find(r=>r.id===e.target.value);update({room_id:linked?.id || null,room_type_id:linked?.room_type_id || image.room_type_id});}}><option value="">Không gắn phòng</option>{(draft.rooms || []).filter(r => r.dormitory_id === image.dormitory_id).map(r => <option key={r.id} value={r.id}>{r.building} · {r.number}</option>)}</select></Field>
            <Text label="Nguồn / người cung cấp" value={image.credit} onChange={credit => update({credit})} /><Text label="Liên kết nguồn (nếu có)" value={image.source_url} onChange={source_url => update({source_url})} />
            <button className={button + " text-red-700"} onClick={() => {if(confirm("Gỡ ảnh khỏi bản nháp?"))change({...draft,images:draft.images.filter((_,i) => i!==index)});}}>Gỡ ảnh</button></article>;
        })}</div></div>}
        {tab === "facts" && <div className="space-y-5"><p className="text-sm text-slate-500">Cập nhật thông tin phí, điện nước, đăng ký, nội quy, liên hệ… để trang và chatbot dùng chung. Giữ ý nghĩa của từng mục có sẵn.</p>
          <button className={button} onClick={() => change({...draft,facts:[...draft.facts,{id:"fact-"+uid(),title:"Thông tin mới",content:"",source_id:"submitted",tags:["overview"]}]})}>+ Thêm thông tin</button>
          {draft.facts.map((fact,index) => {const update=(patch:Partial<typeof fact>)=>change({...draft,facts:draft.facts.map((f,i)=>i===index?{...f,...patch}:f)});return <section key={fact.id} className="grid gap-3 rounded-xl border p-4 md:grid-cols-2">
            <Text label="Tiêu đề" value={fact.title} onChange={title=>update({title})} /><Field label="Nguồn"><select className={input} value={fact.source_id} onChange={e=>update({source_id:e.target.value})}>{draft.sources.map(s=><option key={s.id} value={s.id}>{s.title}</option>)}</select></Field>
            <div className="md:col-span-2"><Text label="Nội dung" value={fact.content} multiline onChange={content=>update({content})} /></div>
            <Field label="Chủ đề (cách nhau dấu phẩy)"><input key={fact.id+fact.tags.join(",")} className={input} defaultValue={fact.tags.join(",")} onBlur={e=>update({tags:e.target.value.split(",").map(t=>t.trim()).filter(Boolean)})} /></Field>
            {!coreFacts.has(fact.id) && <button className={button+" self-end text-red-700"} onClick={()=>change({...draft,facts:draft.facts.filter(f=>f.id!==fact.id)})}>Gỡ mục</button>}</section>;})}</div>}
        {tab === "sources" && <div className="space-y-4"><button className={button} onClick={()=>change({...draft,sources:[...draft.sources,{id:"source-"+uid(),title:"Nguồn mới",url:null,year:null,note:""}]})}>+ Thêm nguồn</button>{draft.sources.map((source,index)=>{
          const update=(patch:Partial<typeof source>)=>change({...draft,sources:draft.sources.map((s,i)=>i===index?{...s,...patch}:s)});
          return <section key={source.id} className="grid gap-3 rounded-xl border p-4 md:grid-cols-2"><Text label="Tên nguồn" value={source.title} onChange={title=>update({title})}/><Text label="Liên kết (để trống nếu do admin cung cấp)" value={source.url||""} onChange={v=>update({url:v||null})}/><Text label="Năm nguồn" type="number" value={source.year??""} onChange={v=>update({year:v?Number(v):null})}/><Text label="Lưu ý nguồn" value={source.note} onChange={note=>update({note})}/></section>;
        })}</div>}
        {tab === "audit" && <div className="space-y-3"><p className="text-sm text-slate-500">20 thao tác gần nhất. Bản nháp và phiên bản đã công bố được giữ riêng.</p>{detail.audit?.map(log=><p key={log.id} className="rounded-xl border p-3 text-sm">{new Date(log.created_at).toLocaleString("vi-VN")} · {log.actor_name || "Hệ thống"} · {({create:"Tạo năm",save_draft:"Lưu bản nháp",publish:"Công bố",archive:"Lưu trữ",restore:"Khôi phục",import_2026_user_catalog:"Cập nhật 27 loại phòng năm 2026"} as Record<string,string>)[log.action] || log.action}</p>)}</div>}
      </fieldset>
    </>}
  </div>;
}
