import Link from "next/link";
import { notFound } from "next/navigation";
import { getListing, type ApiError } from "@/lib/api";
import { getCurrentUser } from "@/lib/current-user";
import { formatArea, formatDistance, formatPrice, riskBadge } from "@/lib/format";
import DeleteListingButton from "./DeleteListingButton";

export const dynamic = "force-dynamic";

export default async function ListingDetailPage({
  params,
}: {
  params: { id: string };
}) {
  let listing;
  try {
    listing = await getListing(params.id);
  } catch (e) {
    if ((e as ApiError).status === 404) notFound();
    throw e;
  }

  const user = await getCurrentUser();
  const canManage = Boolean(user) && listing.source === "user";
  const badge = riskBadge(listing.risk_level);

  return (
    <main className="min-h-screen bg-slate-50 p-4 sm:p-8">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="text-sm text-emerald-600 hover:text-emerald-700">
          ← Về danh sách
        </Link>

        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          {listing.images.length > 0 ? (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {listing.images.map((src, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={i}
                  src={src}
                  alt={`${listing.title} - ảnh ${i + 1}`}
                  className="h-40 w-full rounded object-cover"
                />
              ))}
            </div>
          ) : (
            <div className="flex h-40 w-full items-center justify-center rounded bg-slate-100 text-sm text-slate-400">
              Không có ảnh
            </div>
          )}

          <div className="mt-4 flex items-start justify-between gap-3">
            <h1 className="text-2xl font-bold text-slate-800">{listing.title}</h1>
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}
            >
              {badge.label}
            </span>
          </div>

          <p className="mt-2 text-xl font-semibold text-emerald-700">
            {formatPrice(listing.price)}
          </p>

          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
            {listing.area != null && <span>{formatArea(listing.area)}</span>}
            {listing.district && <span>{listing.district}</span>}
            {listing.distance_to_ctu != null && (
              <span>{formatDistance(listing.distance_to_ctu)}</span>
            )}
          </div>

          {listing.address && (
            <p className="mt-2 text-sm text-slate-600">Địa chỉ: {listing.address}</p>
          )}

          {listing.freshness_label && (
            <p className="mt-1 text-xs text-slate-400">{listing.freshness_label}</p>
          )}

          {listing.description && (
            <p className="mt-4 whitespace-pre-line text-slate-700">
              {listing.description}
            </p>
          )}

          {listing.source_url && (
            <p className="mt-4">
              <a
                href={listing.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-emerald-600 hover:text-emerald-700"
              >
                Xem nguồn gốc
              </a>
            </p>
          )}

          {listing.quality_score != null && (
            <p className="mt-2 text-xs text-slate-400">
              Điểm chất lượng: {(listing.quality_score * 100).toFixed(0)}%
            </p>
          )}

          {canManage && (
            <div className="mt-6 flex gap-3">
              <Link
                href={`/listings/${listing.id}/edit`}
                className="rounded border border-slate-300 px-4 py-2 font-medium text-slate-700 hover:bg-slate-100"
              >
                Sửa
              </Link>
              <DeleteListingButton id={listing.id} />
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
