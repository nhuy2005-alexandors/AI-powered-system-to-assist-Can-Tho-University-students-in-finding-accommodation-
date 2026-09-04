"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function ListingActions({
  listingId,
  loggedIn,
  sourceUrl,
}: {
  listingId: number;
  loggedIn: boolean;
  sourceUrl?: string | null;
}) {
  const [saved, setSaved] = useState(false);
  const [compared, setCompared] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ids = JSON.parse(localStorage.getItem("compare-listings") || "[]") as number[];
    setCompared(ids.includes(listingId));
    if (loggedIn) {
      void fetch("/api/favorites")
        .then((response) => response.ok ? response.json() : [])
        .then((items: Array<{ listing: { id: number } }>) => {
          setSaved(items.some((item) => item.listing.id === listingId));
        })
        .catch(() => undefined);
      void fetch("/api/interactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ listing_id: listingId, type: "view" }),
      });
    }
  }, [listingId, loggedIn]);

  async function toggleFavorite() {
    if (!loggedIn) {
      setError("Vui lòng đăng nhập để lưu yêu thích.");
      return;
    }
    const response = await fetch(`/api/favorites/${listingId}`, { method: saved ? "DELETE" : "PUT" });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail || "Không thể cập nhật yêu thích");
      return;
    }
    setSaved(!saved);
    setError(null);
  }

  function toggleCompare() {
    const ids = JSON.parse(localStorage.getItem("compare-listings") || "[]") as number[];
    const next = ids.includes(listingId)
      ? ids.filter((id) => id !== listingId)
      : [...ids.slice(-3), listingId];
    localStorage.setItem("compare-listings", JSON.stringify(next));
    setCompared(next.includes(listingId));
  }

  function recordSourceClick() {
    if (!loggedIn) return;
    void fetch("/api/interactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ listing_id: listingId, type: "click_source" }),
    });
  }

  return (
    <div>
      <div className="flex flex-col gap-2.5">
        {sourceUrl ? (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={recordSourceClick}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3.5 text-[15px] font-semibold text-white transition hover:bg-navy"
          >
            Liên hệ từ tin gốc
            <span aria-hidden="true">↗</span>
          </a>
        ) : (
          <div className="rounded-xl bg-slate-100 px-4 py-3 text-center text-sm font-medium text-ink-muted">
            Chưa có thông tin liên hệ
          </div>
        )}
        <button
          type="button"
          onClick={() => void toggleFavorite()}
          className={`w-full rounded-xl border px-4 py-3 text-sm font-semibold transition ${
            saved
              ? "border-rose-200 bg-rose-50 text-rose-700"
              : "border-line text-primary hover:border-primary/40 hover:bg-primary-soft"
          }`}
        >
          {saved ? "♥ Đã lưu tin" : "♡ Lưu tin này"}
        </button>
        <button
          type="button"
          onClick={toggleCompare}
          className="w-full rounded-xl border border-line px-4 py-3 text-sm font-semibold text-ink-soft transition hover:bg-tint"
        >
          {compared ? "Bỏ so sánh" : "Thêm vào so sánh"}
        </button>
        {compared && (
          <Link
            href="/compare"
            className="text-center text-sm font-semibold text-primary-bright hover:underline"
          >
            Mở bảng so sánh →
          </Link>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}
    </div>
  );
}
