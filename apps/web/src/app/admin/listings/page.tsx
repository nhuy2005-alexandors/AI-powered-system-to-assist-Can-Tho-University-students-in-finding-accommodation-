import Link from "next/link";
import { redirect } from "next/navigation";
import { getAdminListings, type AdminListingStatus } from "@/lib/api";
import { getAccessToken } from "@/lib/session";
import AdminListingsTable from "./AdminListingsTable";

const VALID_STATUS = new Set(["active", "flagged", "hidden", "expired"]);

export default async function AdminListingsPage({ searchParams }: { searchParams: { q?: string; status?: string; page?: string } }) {
  const token = getAccessToken();
  if (!token) redirect("/login?next=/admin/listings");
  const status = VALID_STATUS.has(searchParams.status || "") ? (searchParams.status as AdminListingStatus) : undefined;
  const page = Math.max(1, Number(searchParams.page) || 1);
  const result = await getAdminListings(token, { q: searchParams.q, status, page, size: 50 });
  const totalPages = Math.max(1, Math.ceil(result.total / 50));
  return (
    <div className="mx-auto max-w-[1500px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-emerald-600">Nội dung</p>
          <h1 className="mt-1 text-3xl font-extrabold text-slate-950">Quản lý bài tin phòng trọ</h1>
          <p className="mt-2 text-sm text-slate-500">Tổng cộng {result.total.toLocaleString("vi-VN")} bài tin từ crawler và người dùng.</p>
        </div>
        <Link href="/listings/new" className="rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white hover:bg-emerald-700">+ Thêm bài tin</Link>
      </div>

      <form className="my-6 flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row">
        <input name="q" defaultValue={searchParams.q || ""} placeholder="Tìm theo tiêu đề hoặc địa chỉ..." className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-emerald-500" />
        <select name="status" defaultValue={status || ""} className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-emerald-500">
          <option value="">Tất cả trạng thái</option>
          <option value="active">Đang hiển thị</option>
          <option value="flagged">Đang cảnh báo</option>
          <option value="hidden">Đã ẩn</option>
          <option value="expired">Hết hạn</option>
        </select>
        <button className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white">Lọc dữ liệu</button>
      </form>

      <AdminListingsTable items={result.items} />
      {totalPages > 1 && (
        <div className="mt-5 flex justify-end gap-2 text-sm font-semibold">
          {page > 1 && <Link href={`/admin/listings?page=${page - 1}`} className="rounded-lg border bg-white px-4 py-2">← Trước</Link>}
          <span className="rounded-lg bg-slate-900 px-4 py-2 text-white">{page}/{totalPages}</span>
          {page < totalPages && <Link href={`/admin/listings?page=${page + 1}`} className="rounded-lg border bg-white px-4 py-2">Sau →</Link>}
        </div>
      )}
    </div>
  );
}
