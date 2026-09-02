import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/current-user";
import AdminSidebar from "./AdminSidebar";

export const dynamic = "force-dynamic";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login?next=/admin");
  if (user.role !== "admin") {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-100 p-5">
        <div className="w-full max-w-md rounded-2xl border border-red-100 bg-white p-8 text-center shadow-xl shadow-slate-200/60">
          <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-red-50 text-3xl text-red-600">!</div>
          <h1 className="mt-5 text-2xl font-extrabold text-slate-900">Không có quyền truy cập</h1>
          <p className="mt-2 text-slate-600">Khu vực này chỉ dành cho tài khoản Admin.</p>
          <Link href="/" className="mt-6 inline-flex rounded-xl bg-emerald-600 px-5 py-3 font-semibold text-white hover:bg-emerald-700">Về trang chính</Link>
        </div>
      </main>
    );
  }
  return (
    <div className="min-h-screen bg-[#f3f6f9] text-slate-900">
      <AdminSidebar user={user} />
      <div className="min-w-0 lg:pl-72">
        <header className="sticky top-0 z-20 hidden h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-8 backdrop-blur lg:flex">
          <div>
            <p className="text-sm font-semibold text-slate-900">Hệ thống quản lý Trọ CTU</p>
            <p className="text-xs text-slate-500">Theo dõi dữ liệu, rủi ro và hoạt động cộng đồng</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">● Hệ thống hoạt động</span>
            <Link href="/" className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Xem trang người dùng ↗</Link>
          </div>
        </header>
        <main className="p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
