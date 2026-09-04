import { redirect } from "next/navigation";
import Link from "next/link";
import { getAdminReports, getAdminSummary } from "@/lib/api";
import { getAccessToken } from "@/lib/session";
export default async function AdminPage() {
  const token = getAccessToken();
  if (!token) redirect("/login?next=/admin");
  const [reportList, summary] = await Promise.all([
    getAdminReports(token, "pending"),
    getAdminSummary(token),
  ]);
  const stats = [
    { label: "Tổng bài tin", value: summary.total_listings, tone: "blue", icon: "▤" },
    { label: "Tin hoạt động", value: summary.active_listings, tone: "emerald", icon: "✓" },
    { label: "Báo cáo chờ", value: summary.pending_reports, tone: "red", icon: "⚑" },
    { label: "Người dùng", value: summary.total_users, tone: "violet", icon: "♙" },
  ] as const;
  const tone = {
    blue: "bg-blue-50 text-blue-700",
    emerald: "bg-emerald-50 text-emerald-700",
    red: "bg-red-50 text-red-700",
    violet: "bg-violet-50 text-violet-700",
  };
  return (
    <div className="mx-auto max-w-[1500px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-emerald-600">Tổng quan</p>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950">Dashboard quản trị</h1>
          <p className="mt-2 text-sm text-slate-500">Thông tin cập nhật trực tiếp từ hệ thống phòng trọ.</p>
        </div>
        <p className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-500">Cập nhật vừa xong</p>
      </div>

      <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => (
          <article key={item.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-500">{item.label}</p>
              <span className={`grid h-10 w-10 place-items-center rounded-xl text-lg font-bold ${tone[item.tone]}`}>{item.icon}</span>
            </div>
            <p className="mt-4 text-3xl font-black text-slate-950">{item.value.toLocaleString("vi-VN")}</p>
          </article>
        ))}
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,.75fr)]">
        <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5">
            <div>
              <h2 className="text-lg font-extrabold text-slate-900">Báo cáo cần xử lý</h2>
              <p className="mt-1 text-sm text-slate-500">Ưu tiên các tin có Risk cao hoặc bị báo cáo lừa đảo.</p>
            </div>
            <Link href="/admin/reports" className="text-sm font-bold text-emerald-700 hover:text-emerald-800">Xem tất cả →</Link>
          </div>
          {reportList.items.length === 0 ? (
            <div className="p-10 text-center text-sm text-slate-500">Hiện không có báo cáo nào đang chờ xử lý.</div>
          ) : (
            <div className="divide-y divide-slate-100">
              {reportList.items.slice(0, 6).map((report) => (
                <Link key={report.id} href="/admin/reports" className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-red-50 font-bold text-red-600">!</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-bold text-slate-900">{report.listing_title}</span>
                    <span className="mt-1 block truncate text-xs text-slate-500">{report.note || report.reason}</span>
                  </span>
                  <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-700">Risk {Math.round((report.risk_score || 0) * 100)}%</span>
                </Link>
              ))}
            </div>
          )}
        </article>

        <article className="rounded-2xl bg-gradient-to-br from-[#0b1f33] to-[#123d5a] p-6 text-white shadow-sm">
          <p className="text-sm font-semibold text-emerald-300">Tình trạng kiểm duyệt</p>
          <p className="mt-3 text-4xl font-black">{summary.pending_reports}</p>
          <p className="mt-1 text-sm text-slate-300">báo cáo đang chờ từ {summary.reporting_users} người dùng</p>
          <div className="mt-6 space-y-3 border-t border-white/10 pt-5 text-sm">
            <div className="flex justify-between"><span className="text-slate-300">Tin bị cảnh báo</span><strong>{summary.flagged_listings}</strong></div>
            <div className="flex justify-between"><span className="text-slate-300">Tin đã ẩn</span><strong>{summary.hidden_listings}</strong></div>
          </div>
          <Link href="/admin/listings?status=flagged" className="mt-6 block rounded-xl bg-white px-4 py-3 text-center text-sm font-extrabold text-slate-900 hover:bg-emerald-50">Kiểm tra bài tin rủi ro</Link>
        </article>
      </section>
    </div>
  );
}
