"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { ReportReason } from "@/lib/api";

const REASONS: { value: ReportReason; label: string }[] = [
  { value: "wrong_price", label: "Sai giá hoặc thông tin" },
  { value: "expired", label: "Phòng đã hết / tin đã cũ" },
  { value: "scam", label: "Nghi ngờ lừa đảo" },
  { value: "other", label: "Lý do khác" },
];

export default function ReportButton({
  listingId,
  loggedIn,
  canReport,
}: {
  listingId: number;
  loggedIn: boolean;
  canReport: boolean;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<ReportReason>("expired");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!loggedIn) {
    return (
      <Link
        href={`/login?next=/listings/${listingId}`}
        className="rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
      >
        Đăng nhập để báo cáo
      </Link>
    );
  }

  if (!canReport) return null;

  async function submit() {
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`/api/listings/${listingId}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, note: note.trim() || null }),
      });
      const body = (await response.json()) as { detail?: string };
      if (!response.ok) throw new Error(body.detail || "Không gửi được báo cáo");
      setSuccess(true);
      setMessage("Đã gửi báo cáo. Admin sẽ kiểm tra tin này.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Không gửi được báo cáo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
      >
        Báo cáo tin
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Báo cáo tin không chính xác</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Báo cáo sẽ được chuyển riêng cho Admin và được đưa vào điểm Risk.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-2xl leading-none text-slate-400 hover:text-slate-700"
                aria-label="Đóng"
              >
                ×
              </button>
            </div>

            {!success ? (
              <div className="mt-5 space-y-4">
                <fieldset className="space-y-2">
                  <legend className="text-sm font-semibold text-slate-700">Lý do</legend>
                  {REASONS.map((item) => (
                    <label
                      key={item.value}
                      className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-200 p-3 hover:bg-slate-50"
                    >
                      <input
                        type="radio"
                        name="report-reason"
                        value={item.value}
                        checked={reason === item.value}
                        onChange={() => setReason(item.value)}
                      />
                      <span className="text-sm text-slate-700">{item.label}</span>
                    </label>
                  ))}
                </fieldset>
                <label className="block text-sm font-semibold text-slate-700">
                  Ghi chú (không bắt buộc)
                  <textarea
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    maxLength={1000}
                    rows={4}
                    className="mt-2 w-full rounded-lg border border-slate-300 p-3 font-normal outline-none focus:border-red-400"
                    placeholder="Mô tả điều bạn đã kiểm chứng..."
                  />
                </label>
                <button
                  type="button"
                  onClick={submit}
                  disabled={loading}
                  className="w-full rounded-lg bg-red-600 px-4 py-3 font-semibold text-white hover:bg-red-700 disabled:opacity-60"
                >
                  {loading ? "Đang gửi..." : "Gửi báo cáo"}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="mt-5 w-full rounded-lg bg-emerald-600 px-4 py-3 font-semibold text-white"
              >
                Hoàn tất
              </button>
            )}

            {message && (
              <p className={`mt-4 text-sm ${success ? "text-emerald-700" : "text-red-700"}`}>
                {message}
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
