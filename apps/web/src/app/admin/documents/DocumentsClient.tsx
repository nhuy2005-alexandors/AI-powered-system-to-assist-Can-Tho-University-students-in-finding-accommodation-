"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

type Document = {
  id: number; title: string; category: string; source_path: string; document_type: string;
  status: string; admin_enabled: boolean; page_count: number; chunk_count: number;
  error_message: string | null; updated_at: string;
};
type Chunk = { id: number; heading: string | null; content: string; page_from: number | null; page_to: number | null; quality_warning: string | null };
type Detail = { document: Document; chunks: Chunk[]; has_more: boolean };
const statusName: Record<string, string> = { ready: "Đã lập chỉ mục", indexing: "Đang xử lý", failed: "Xử lý thất bại" };
const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold disabled:opacity-50";
const input = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Không thể xử lý yêu cầu");
  return data;
}

export default function DocumentsClient() {
  const [items, setItems] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [schema, setSchema] = useState("");
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [enabled, setEnabled] = useState("");
  const [status, setStatus] = useState("");
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const detailVersion = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    setBusy(true); setError("");
    const params = new URLSearchParams({ q: query, offset: String(page * 20), limit: "20" });
    if (enabled) params.set("enabled", enabled);
    if (status) params.set("status", status);
    request<{ items: Document[]; total: number; corpus_schema: string }>(`/api/admin/documents?${params}`, { signal: controller.signal })
      .then(data => { setItems(data.items); setTotal(data.total); setSchema(data.corpus_schema); })
      .catch(e => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [query, page, enabled, status, revision]);

  async function open(id: number) {
    const version = ++detailVersion.current;
    setDetail(null); setError(""); setNotice("");
    try {
      const data = await request<Detail>(`/api/admin/documents/${id}`);
      if (version !== detailVersion.current) return;
      setDetail(data); setTitle(data.document.title); setCategory(data.document.category);
    } catch (e) { if (version === detailVersion.current) setError((e as Error).message); }
  }

  async function update(changes: Record<string, unknown>) {
    if (!detail) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const data = await request<{ document: Document }>(`/api/admin/documents/${detail.document.id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(changes),
      });
      setDetail(current => current && ({ ...current, document: data.document }));
      setItems(current => current.map(item => item.id === data.document.id ? data.document : item));
      setTitle(data.document.title); setCategory(data.document.category);
      setNotice("Đã cập nhật tài liệu. Câu trả lời tiếp theo sử dụng trạng thái mới.");
      setRevision(value => value + 1);
    } catch (e) { setError((e as Error).message); }
    finally { setSaving(false); }
  }

  async function more() {
    if (!detail) return;
    const id = detail.document.id, version = detailVersion.current;
    setSaving(true); setError("");
    try {
      const data = await request<Detail>(`/api/admin/documents/${id}?offset=${detail.chunks.length}`);
      if (version === detailVersion.current) setDetail(current => current && ({ ...data, chunks: [...current.chunks, ...data.chunks] }));
    } catch (e) { setError((e as Error).message); }
    finally { setSaving(false); }
  }

  return <div className="mt-6 space-y-5">
    <form className="flex flex-wrap gap-3" onSubmit={(e: FormEvent) => { e.preventDefault(); setPage(0); setQuery(search); }}>
      <input aria-label="Tìm tài liệu" className={`${input} max-w-md`} placeholder="Tìm theo tên, nhóm hoặc nguồn..." value={search} onChange={e => setSearch(e.target.value)} />
      <select aria-label="Trạng thái sử dụng" className={`${input} max-w-48`} value={enabled} onChange={e => { setPage(0); setEnabled(e.target.value); }}>
        <option value="">Tất cả nguồn</option><option value="true">Được phép sử dụng</option><option value="false">Đã tắt</option>
      </select>
      <select aria-label="Trạng thái xử lý" className={`${input} max-w-48`} value={status} onChange={e => { setPage(0); setStatus(e.target.value); }}>
        <option value="">Tất cả trạng thái</option>{Object.entries(statusName).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
      <button className={button}>Tìm kiếm</button>
    </form>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
    <p className="text-sm text-slate-500">{total} tài liệu · Bộ dữ liệu: {schema || "Đang tải"}</p>
    {busy ? <p role="status">Đang tải tài liệu...</p> : <>
      <div className="space-y-3 md:hidden">
        {items.map(item => <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="break-words font-bold">{item.title}</h2>
          <p className="mt-1 break-all text-xs text-slate-500">{item.source_path}</p>
          <p className="mt-3 text-sm text-slate-600">Nhóm: {item.category} · {item.page_count} trang · {item.chunk_count} đoạn</p>
          <div className="mt-3 flex items-center justify-between gap-3">
            <div className="text-sm"><p>{statusName[item.status] || item.status}</p><p className={item.admin_enabled ? "text-emerald-700" : "text-amber-700"}>{item.admin_enabled ? "Được phép sử dụng" : "Đã tắt"}</p></div>
            <button disabled={saving} className={button} onClick={() => open(item.id)}>Kiểm tra</button>
          </div>
        </article>)}
        {!items.length && <p className="rounded-xl bg-white p-5 text-sm text-slate-500">Không có tài liệu phù hợp.</p>}
      </div>
      <div className="hidden overflow-x-auto rounded-2xl border border-slate-200 bg-white md:block">
        <table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-600"><tr>
          <th className="p-4">Tài liệu</th><th className="p-4">Nhóm</th><th className="p-4">Trạng thái</th><th className="p-4">Nội dung</th><th className="p-4">Thao tác</th>
        </tr></thead><tbody>{items.map(item => <tr key={item.id} className="border-t border-slate-100">
          <td className="max-w-md break-words p-4"><p className="font-bold">{item.title}</p><p className="mt-1 text-xs text-slate-500">{item.source_path}</p></td>
          <td className="p-4">{item.category}</td><td className="p-4"><p>{statusName[item.status] || item.status}</p><p className={item.admin_enabled ? "text-emerald-700" : "text-amber-700"}>{item.admin_enabled ? "Được phép sử dụng" : "Đã tắt"}</p></td>
          <td className="p-4">{item.page_count} trang · {item.chunk_count} đoạn</td><td className="p-4"><button disabled={saving} className={button} onClick={() => open(item.id)}>Kiểm tra</button></td>
        </tr>)}</tbody></table>
        {!items.length && <p className="p-6 text-slate-500">Không có tài liệu phù hợp.</p>}
      </div>
      <div className="flex items-center gap-3"><button className={button} disabled={page === 0} onClick={() => setPage(page - 1)}>Trước</button><span className="text-sm">Trang {page + 1}</span><button className={button} disabled={(page + 1) * 20 >= total} onClick={() => setPage(page + 1)}>Sau</button></div>
    </>}
    {detail && <section aria-label="Chi tiết tài liệu" className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between gap-3"><h2 className="text-xl font-bold">Kiểm tra tài liệu</h2><button className={button} disabled={saving} onClick={() => { ++detailVersion.current; setDetail(null); }}>Đóng</button></div>
      <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={e => { e.preventDefault(); update({ title, category }); }}>
        <label className="text-sm font-semibold">Tên tài liệu<input required maxLength={300} className={`${input} mt-1`} value={title} onChange={e => setTitle(e.target.value)} /></label>
        <label className="text-sm font-semibold">Nhóm tài liệu<input required maxLength={80} className={`${input} mt-1`} value={category} onChange={e => setCategory(e.target.value)} /></label>
        <div className="flex flex-wrap gap-3 sm:col-span-2"><button disabled={saving} className={`${button} bg-emerald-600 text-white`}>Lưu thông tin</button>
          <button type="button" className={button} disabled={saving || (!detail.document.admin_enabled && (detail.document.status !== "ready" || !detail.document.chunk_count))} onClick={() => update({ admin_enabled: !detail.document.admin_enabled })}>{detail.document.admin_enabled ? "Tắt sử dụng tài liệu" : "Bật sử dụng tài liệu"}</button>
        </div>
      </form>
      <p className="mt-4 break-all text-xs text-slate-500">Nguồn: {detail.document.source_path} · Cập nhật: {new Date(detail.document.updated_at).toLocaleString("vi-VN")}</p>
      {detail.document.error_message && <p className="mt-3 text-sm text-amber-800">{detail.document.error_message}</p>}
      <div className="mt-5 space-y-3">{detail.chunks.map(chunk => <article key={chunk.id} className="rounded-xl border border-slate-200 p-4">
        <h3 className="font-semibold">{chunk.heading || "Nội dung"} <span className="text-xs text-slate-500">· Trang {chunk.page_from ?? "?"}–{chunk.page_to ?? "?"}</span></h3>
        {chunk.quality_warning && <p className="mt-1 text-sm text-amber-700">Cần kiểm tra chất lượng: {chunk.quality_warning}</p>}
        <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-slate-700">{chunk.content}</p>
      </article>)}</div>
      {!detail.chunks.length && <p className="mt-4 text-sm text-slate-500">Chưa có nội dung được trích xuất.</p>}
      {detail.has_more && <button disabled={saving} className={`${button} mt-4`} onClick={more}>Xem thêm nội dung</button>}
    </section>}
  </div>;
}
