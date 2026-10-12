"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { AdminReviewItem } from "@/lib/api";

export default function ReviewQueue({ items }: { items: AdminReviewItem[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function moderate(id: number, action: "approve" | "hide") {
    setBusy(id); setError(null);
    try {
      const response = await fetch(`/api/admin/reviews/${id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Không duyệt được đánh giá");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không duyệt được đánh giá");
    } finally { setBusy(null); }
  }
  return (
    <div className="space-y-4">
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}
      {!items.length && <p className="rounded-lg bg-white p-6">Không có bình luận chờ duyệt.</p>}
      {items.map((item) => (
        <article key={item.id} className="rounded-xl border bg-white p-5">
          <Link href={`/listings/${item.listing_id}`} className="font-bold text-emerald-700">{item.listing_title}</Link>
          <p className="mt-2 text-sm text-slate-600">{item.author_name} · {item.rating}/5 sao</p>
          <p className="my-3 whitespace-pre-line">{item.comment}</p>
          <p className="mb-3 text-xs text-slate-500">Mô hình sàng lọc: {item.model_version}</p>
          <div className="flex gap-3">
            <button disabled={busy !== null} onClick={() => moderate(item.id, "approve")} className="rounded-lg bg-emerald-700 px-4 py-2 text-white disabled:opacity-50">Duyệt, giữ hiển thị</button>
            <button disabled={busy !== null} onClick={() => moderate(item.id, "hide")} className="rounded-lg border px-4 py-2 text-red-700 disabled:opacity-50">Ẩn bình luận</button>
          </div>
        </article>
      ))}
    </div>
  );
}
