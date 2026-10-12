import Link from "next/link";
import { redirect } from "next/navigation";
import { getFlaggedReviews } from "@/lib/api";
import { reauthUrl } from "@/lib/current-user";
import { getAccessToken } from "@/lib/session";
import ReviewQueue from "./ReviewQueue";

export default async function AdminReviewsPage({ searchParams }: { searchParams: { page?: string } }) {
  const token = getAccessToken();
  if (!token) redirect(reauthUrl("/admin/reviews"));
  const page = Math.max(1, Math.floor(Number(searchParams.page) || 1));
  const data = await getFlaggedReviews(token, page);
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-3xl font-bold">Duyệt đánh giá nhà trọ</h1>
      <p className="my-4 text-sm text-slate-600">
        {data.total} bình luận cần xem xét. Phân tích cảm xúc chỉ hỗ trợ sàng lọc;
        phản hồi tiêu cực có thể là trải nghiệm hợp lệ của người thuê.
      </p>
      <ReviewQueue items={data.items} />
      <nav className="mt-5 flex gap-4 text-sm">
        {page > 1 && <Link href={`/admin/reviews?page=${page - 1}`}>← Trước</Link>}
        <span>Trang {page}</span>
        {page * 50 < data.total && <Link href={`/admin/reviews?page=${page + 1}`}>Sau →</Link>}
      </nav>
    </div>
  );
}
