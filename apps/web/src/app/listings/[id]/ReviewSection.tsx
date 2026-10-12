"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ReviewList, ReviewOut } from "@/lib/api";


const STAR_LABELS = ["Rất tệ", "Chưa tốt", "Bình thường", "Tốt", "Rất tốt"];

function Stars({ value, label }: { value: number; label?: string }) {
  return (
    <span aria-label={label || `${value} trên 5 sao`} className="tracking-[.12em]">
      {Array.from({ length: 5 }, (_, index) => (
        <span key={index} className={index < Math.round(value) ? "text-amber-500" : "text-slate-300"}>
          ★
        </span>
      ))}
    </span>
  );
}

function nextReviewList(current: ReviewList, review: ReviewOut): ReviewList {
  const previousTotal = current.summary.total;
  const total = previousTotal + 1;
  const previousAverage = current.summary.average_rating || 0;
  return {
    summary: {
      total,
      average_rating: Number(((previousAverage * previousTotal + review.rating) / total).toFixed(1)),
      rating_counts: {
        ...current.summary.rating_counts,
        [review.rating]: (current.summary.rating_counts[review.rating] || 0) + 1,
      },
    },
    items: [review, ...current.items],
  };
}

export default function ReviewSection({
  listingId,
  initialData,
  loggedIn,
  canReview,
}: {
  listingId: number;
  initialData: ReviewList;
  loggedIn: boolean;
  canReview: boolean;
}) {
  const [data, setData] = useState(initialData);
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const shownRating = hoveredRating || rating;
  const ratingHint = shownRating ? STAR_LABELS[shownRating - 1] : "Chọn mức đánh giá";
  const distributions = useMemo(
    () => [5, 4, 3, 2, 1].map((star) => ({
      star,
      count: data.summary.rating_counts[star] || 0,
      width: data.summary.total
        ? ((data.summary.rating_counts[star] || 0) / data.summary.total) * 100
        : 0,
    })),
    [data.summary],
  );

  async function submitReview() {
    if (!rating) {
      setMessage("Vui lòng chọn từ 1 đến 5 sao.");
      return;
    }
    if (comment.trim().length < 10) {
      setMessage("Bình luận cần có ít nhất 10 ký tự.");
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`/api/listings/${listingId}/reviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, comment: comment.trim() }),
      });
      const body = (await response.json()) as ReviewOut & { detail?: string };
      if (!response.ok) throw new Error(body.detail || "Không gửi được đánh giá");
      setData((current) => nextReviewList(current, body));
      setSubmitted(true);
      setMessage(
        body.is_flagged
          ? "Đã gửi đánh giá và chuyển cho quản trị viên rà soát."
          : "Đã đăng đánh giá của bạn.",
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Không gửi được đánh giá");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-xl font-bold text-ink">Đánh giá nhà trọ</h2>
      <div className="grid gap-5 md:grid-cols-[190px_minmax(0,1fr)] md:items-center">
        <div className="rounded-2xl bg-slate-50 p-5 text-center">
          <p className="text-4xl font-black text-ink">
            {data.summary.average_rating?.toFixed(1) || "—"}
          </p>
          <div className="mt-1 text-xl"><Stars value={data.summary.average_rating || 0} /></div>
          <p className="mt-2 text-sm text-ink-muted">{data.summary.total} đánh giá</p>
        </div>
        <div className="space-y-2">
          {distributions.map(({ star, count, width }) => (
            <div key={star} className="grid grid-cols-[32px_1fr_28px] items-center gap-2 text-xs text-ink-muted">
              <span>{star} ★</span>
              <span className="h-2 overflow-hidden rounded-full bg-slate-100">
                <span className="block h-full rounded-full bg-amber-400" style={{ width: `${width}%` }} />
              </span>
              <span className="text-right">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {!loggedIn ? (
        <div className="mt-5 rounded-2xl border border-dashed border-line bg-slate-50 p-4 text-sm text-ink-muted">
          <Link href={`/login?next=/listings/${listingId}`} className="font-bold text-primary-bright hover:underline">
            Đăng nhập
          </Link>{" "}để chấm sao và chia sẻ trải nghiệm thực tế.
        </div>
      ) : !canReview ? (
        <p className="mt-5 rounded-2xl bg-slate-50 p-4 text-sm text-ink-muted">
          Tin này hiện không nhận đánh giá từ tài khoản của bạn.
        </p>
      ) : !submitted ? (
        <div className="mt-5 rounded-2xl border border-line-soft bg-slate-50 p-4 sm:p-5">
          <h3 className="font-bold text-ink">Bạn thấy phòng này thế nào?</h3>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <div className="flex" onMouseLeave={() => setHoveredRating(0)}>
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoveredRating(star)}
                  className={`px-1 text-3xl transition hover:scale-110 ${star <= shownRating ? "text-amber-500" : "text-slate-300"}`}
                  aria-label={`${star} sao - ${STAR_LABELS[star - 1]}`}
                >
                  ★
                </button>
              ))}
            </div>
            <span className="text-sm font-semibold text-ink-muted">{ratingHint}</span>
          </div>
          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            minLength={10}
            maxLength={2000}
            rows={4}
            className="mt-3 w-full rounded-xl border border-line bg-white p-3 text-sm outline-none transition focus:border-primary"
            placeholder="Chia sẻ về tình trạng phòng, chủ trọ, giá điện nước, an ninh..."
          />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-ink-muted">
              Phân tích cảm xúc hỗ trợ sàng lọc bình luận; quản trị viên quyết định việc kiểm duyệt.
            </p>
            <button
              type="button"
              onClick={submitReview}
              disabled={loading}
              className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:brightness-110 disabled:opacity-60"
            >
              {loading ? "Đang phân tích..." : "Đăng đánh giá"}
            </button>
          </div>
        </div>
      ) : null}

      {message && (
        <p className={`mt-3 rounded-xl px-4 py-3 text-sm ${submitted ? "bg-emerald-50 text-emerald-800" : "bg-rose-50 text-rose-700"}`}>
          {message}
        </p>
      )}

      <div className="mt-6 space-y-4">
        {data.items.length ? data.items.map((review) => (
          <article key={review.id} className="border-t border-line-soft pt-4 first:border-0 first:pt-0">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-bold text-ink">{review.author_name}</p>
                <div className="mt-0.5 flex flex-wrap items-center gap-2 text-sm">
                  <Stars value={review.rating} />
                  <span className="text-xs text-ink-muted">
                    {new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(review.created_at))}
                  </span>
                </div>
              </div>
              {review.is_flagged && (
                <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                  Đang được rà soát
                </span>
              )}
            </div>
            <p className="mt-2 whitespace-pre-line text-sm leading-6 text-ink-soft">{review.comment}</p>
          </article>
        )) : (
          <p className="rounded-2xl border border-dashed border-line p-5 text-center text-sm text-ink-muted">
            Chưa có đánh giá nào. Hãy là người đầu tiên chia sẻ trải nghiệm.
          </p>
        )}
      </div>
    </section>
  );
}
