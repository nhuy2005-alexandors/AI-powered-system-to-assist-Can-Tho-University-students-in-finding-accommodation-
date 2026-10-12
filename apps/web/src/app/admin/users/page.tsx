import { redirect } from "next/navigation";
import { getAdminUsers } from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export default async function AdminUsersPage({ searchParams }: { searchParams: { q?: string; page?: string } }) {
  const token = getAccessToken();
  if (!token) redirect("/login?next=/admin/users");
  const page = Math.max(1, Number(searchParams.page) || 1);
  const result = await getAdminUsers(token, { q: searchParams.q, page, size: 50 });
  return (
    <div className="mx-auto max-w-[1500px]">
      <div>
        <p className="text-sm font-bold uppercase tracking-[0.14em] text-emerald-600">Tài khoản</p>
        <h1 className="mt-1 text-3xl font-extrabold text-slate-950">Quản lý người dùng</h1>
        <p className="mt-2 text-sm text-slate-500">Theo dõi {result.total.toLocaleString("vi-VN")} tài khoản và hoạt động đóng góp.</p>
      </div>
      <form className="my-6 flex gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <input name="q" defaultValue={searchParams.q || ""} placeholder="Tìm tên hoặc email..." className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-emerald-500" />
        <button className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white">Tìm người dùng</button>
      </form>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs font-bold uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-4">Người dùng</th><th className="px-5 py-4">Vai trò</th><th className="px-5 py-4">Xác minh</th><th className="px-5 py-4">Bài đăng</th><th className="px-5 py-4">Báo cáo đã gửi</th><th className="px-5 py-4">Ngày tham gia</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {result.items.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50/70">
                  <td className="px-5 py-4"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-full bg-blue-50 font-bold text-blue-700">{(user.name || user.email).charAt(0).toUpperCase()}</span><span><strong className="block text-slate-900">{user.name || "Chưa cập nhật tên"}</strong><span className="text-xs text-slate-500">{user.email}</span></span></div></td>
                  <td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${user.role === 'admin' ? 'bg-violet-50 text-violet-700' : 'bg-slate-100 text-slate-600'}`}>{user.role}</span></td>
                  <td className="px-5 py-4 text-xs font-semibold text-slate-600">{user.email_verified ? "✓ Đã xác minh" : "Chưa xác minh"}</td>
                  <td className="px-5 py-4 font-bold text-slate-700">{user.listing_count}</td>
                  <td className="px-5 py-4 font-bold text-slate-700">{user.report_count}</td>
                  <td className="px-5 py-4 text-xs text-slate-500">{new Date(user.created_at).toLocaleDateString("vi-VN")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
