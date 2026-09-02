import Link from "next/link";
import { redirect } from "next/navigation";
import { getAdminReports, getAdminSummary, type ReportStatus } from "@/lib/api";
import { getAccessToken } from "@/lib/session";
import AdminReportQueue from "../AdminReportQueue";

const VALID_STATUS = new Set(["pending", "reviewed", "dismissed"]);

export default async function AdminReportsPage({ searchParams }: { searchParams: { status?: string } }) {
  const token = getAccessToken();
  if (!token) redirect("/login?next=/admin/reports");
  const status = VALID_STATUS.has(searchParams.status || "")
    ? (searchParams.status as ReportStatus)
    : "pending";
  const [reportList, summary] = await Promise.all([
    getAdminReports(token, status),
    getAdminSummary(token),
  ]);
  return (
    <div className="mx-auto max-w-[1500px]">
      <div>
        <p className="text-sm font-bold uppercase tracking-[0.14em] text-emerald-600">Cộng đồng</p>
        <h1 className="mt-1 text-3xl font-extrabold text-slate-950">Kiểm duyệt báo cáo tin</h1>
        <p className="mt-2 text-sm text-slate-500">Đọc nội dung, đối chiếu Risk và quyết định trạng thái bài tin.</p>
      </div>
      <nav className="my-6 flex flex-wrap gap-2">
        {([['pending','Chờ xử lý'],['reviewed','Đã xác nhận'],['dismissed','Đã bác bỏ']] as const).map(([value,label]) => (
          <Link key={value} href={`/admin/reports?status=${value}`} className={`rounded-full px-4 py-2 text-sm font-bold ${status === value ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-600'}`}>{label}</Link>
        ))}
      </nav>
      <AdminReportQueue reports={reportList.items} summary={summary} />
    </div>
  );
}
