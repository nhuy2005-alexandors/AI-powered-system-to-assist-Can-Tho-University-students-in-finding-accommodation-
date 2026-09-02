"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { AdminListingItem, AdminListingStatus } from "@/lib/api";
import { formatPrice } from "@/lib/format";

const STATUS_LABEL: Record<AdminListingStatus, string> = {
  active: "Đang hiển thị",
  flagged: "Cảnh báo",
  hidden: "Đã ẩn",
  expired: "Hết hạn",
};

const STATUS_STYLE: Record<AdminListingStatus, string> = {
  active: "bg-emerald-50 text-emerald-700",
  flagged: "bg-amber-50 text-amber-700",
  hidden: "bg-slate-100 text-slate-600",
  expired: "bg-red-50 text-red-700",
};

export default function AdminListingsTable({ items }: { items: AdminListingItem[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function changeStatus(id: number, status: AdminListingStatus) {
    setBusy(id);
    setError(null);
    try {
      const response = await fetch(`/api/admin/listings/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const body = (await response.json()) as { detail?: string };
      if (!response.ok) throw new Error(body.detail || "Không cập nhật được bài tin");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không cập nhật được bài tin");
    } finally {
      setBusy(null);
    }
  }

  if (items.length === 0) {
    return <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500">Không tìm thấy bài tin phù hợp.</div>;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {error && <p className="border-b border-red-100 bg-red-50 px-5 py-3 text-sm text-red-700">{error}</p>}
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs font-bold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-4">Bài tin</th>
              <th className="px-5 py-4">Nguồn</th>
              <th className="px-5 py-4">Risk / Báo cáo</th>
              <th className="px-5 py-4">Trạng thái</th>
              <th className="px-5 py-4 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/70">
                <td className="max-w-md px-5 py-4">
                  <Link href={`/listings/${item.id}`} className="block truncate font-bold text-slate-900 hover:text-emerald-700">#{item.id} · {item.title}</Link>
                  <p className="mt-1 truncate text-xs text-slate-500">{formatPrice(item.price)} · {item.address || item.district || "Chưa có địa chỉ"}</p>
                </td>
                <td className="px-5 py-4"><span className="rounded-lg bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">{item.source}</span></td>
                <td className="px-5 py-4">
                  <p className={`font-bold ${item.risk_level === "suspicious" ? "text-red-600" : item.risk_level === "caution" ? "text-amber-600" : "text-emerald-600"}`}>{Math.round((item.risk_score || 0) * 100)}% · {item.risk_level}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.report_count} báo cáo</p>
                </td>
                <td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${STATUS_STYLE[item.status]}`}>{STATUS_LABEL[item.status]}</span></td>
                <td className="px-5 py-4 text-right">
                  <select
                    aria-label={`Đổi trạng thái bài tin ${item.id}`}
                    value={item.status}
                    disabled={busy === item.id}
                    onChange={(event) => void changeStatus(item.id, event.target.value as AdminListingStatus)}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none focus:border-emerald-500 disabled:opacity-50"
                  >
                    <option value="active">Hiển thị</option>
                    <option value="flagged">Gắn cảnh báo</option>
                    <option value="hidden">Ẩn tin</option>
                    <option value="expired">Hết hạn</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
