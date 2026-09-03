"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type {
  AdminDashboardSummary,
  AdminReportItem,
  ModerationAction,
} from "@/lib/api";
import { formatPrice } from "@/lib/format";

const REASON_LABEL: Record<string, string> = {
  wrong_price: "Sai giá hoặc thông tin",
  expired: "Phòng đã hết / tin đã cũ",
  scam: "Nghi ngờ lừa đảo",
  other: "Lý do khác",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Chờ xử lý",
  reviewed: "Đã xác nhận",
  dismissed: "Đã bác bỏ",
};

export default function AdminReportQueue({
  reports,
  summary,
}: {
  reports: AdminReportItem[];
  summary: AdminDashboardSummary;
}) {
  const router = useRouter();
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function moderate(reportId: number, action: ModerationAction) {
    const messages: Record<ModerationAction, string> = {
      dismiss: "Bác bỏ các báo cáo đang chờ và giữ tin này?",
      flag: "Xác nhận báo cáo và gắn cảnh báo cho tin này?",
      hide: "Xác nhận báo cáo và ẩn tin khỏi hệ thống?",
    };
    if (!window.confirm(messages[action])) return;
    setBusyId(reportId);
    setError(null);
    try {
      const response = await fetch(`/api/admin/reports/${reportId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const body = (await response.json()) as { detail?: string };
      if (!response.ok) throw new Error(body.detail || "Không xử lý được báo cáo");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không xử lý được báo cáo");
    } finally {
      setBusyId(null);
    }
  }

  const cards = [
    ["Tin trong hệ thống", summary.total_listings],
    ["Tin đang hoạt động", summary.active_listings],
    ["Tin bị cảnh báo", summary.flagged_listings],
    ["Báo cáo chờ xử lý", summary.pending_reports],
  ];

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
          </div>
        ))}
      </div>

      {error && <p className="mt-5 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <div className="mt-6 space-y-4">
        {reports.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-slate-500">
            Không có báo cáo trong mục này.
          </div>
        ) : (
          reports.map((report) => (
            <article key={report.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
                      {REASON_LABEL[report.reason] || report.reason}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                      {STATUS_LABEL[report.status] || report.status}
                    </span>
                    {report.open_report_count > 1 && (
                      <span className="text-xs font-semibold text-red-600">
                        {report.open_report_count} báo cáo đang chờ
                      </span>
                    )}
                  </div>
                  <Link
                    href={`/listings/${report.listing_id}`}
                    className="mt-3 block text-lg font-bold text-slate-900 hover:text-emerald-700"
                  >
                    {report.listing_title}
                  </Link>
                  <p className="mt-1 text-sm text-slate-600">
                    {formatPrice(report.listing_price)}
                    {report.listing_address ? ` · ${report.listing_address}` : ""}
                  </p>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <p>{new Date(report.created_at).toLocaleString("vi-VN")}</p>
                  <p className="mt-1">Người gửi: {report.reporter_name || report.reporter_email || "Ẩn danh"}</p>
                </div>
              </div>

              {report.note && (
                <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                  “{report.note}”
                </div>
              )}

              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
                <p className="text-sm font-semibold text-amber-900">
                  Risk: {Math.round((report.risk_score || 0) * 100)}% · {report.risk_level}
                </p>
                {report.risk_reasons.length > 0 && (
                  <ul className="mt-2 list-disc pl-5 text-sm text-amber-800">
                    {report.risk_reasons.map((reason) => <li key={reason}>{reason}</li>)}
                  </ul>
                )}
              </div>

              {report.status === "pending" && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busyId === report.id}
                    onClick={() => moderate(report.id, "dismiss")}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  >
                    Bác bỏ, giữ tin
                  </button>
                  <button
                    type="button"
                    disabled={busyId === report.id}
                    onClick={() => moderate(report.id, "flag")}
                    className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 disabled:opacity-50"
                  >
                    Gắn cảnh báo
                  </button>
                  <button
                    type="button"
                    disabled={busyId === report.id}
                    onClick={() => moderate(report.id, "hide")}
                    className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    Ẩn tin
                  </button>
                </div>
              )}
            </article>
          ))
        )}
      </div>
    </>
  );
}
