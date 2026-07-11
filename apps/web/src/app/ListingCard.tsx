import Link from "next/link";
import type { ListingOut } from "@/lib/api";
import { formatArea, formatDistance, formatPrice, riskBadge } from "@/lib/format";

export default function ListingCard({ listing }: { listing: ListingOut }) {
  const badge = riskBadge(listing.risk_level);
  const cover = listing.images[0];

  return (
    <Link
      href={`/listings/${listing.id}`}
      className="block rounded-lg border border-slate-200 bg-white shadow-sm transition hover:shadow-md"
    >
      {cover ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={cover}
          alt={listing.title}
          className="h-40 w-full rounded-t-lg object-cover"
        />
      ) : (
        <div className="flex h-40 w-full items-center justify-center rounded-t-lg bg-slate-100 text-sm text-slate-400">
          Không có ảnh
        </div>
      )}

      <div className="space-y-1 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="line-clamp-2 font-medium text-slate-800">{listing.title}</h3>
          <span
            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}
          >
            {badge.label}
          </span>
        </div>

        <p className="font-semibold text-emerald-700">{formatPrice(listing.price)}</p>

        <div className="flex flex-wrap gap-x-3 text-sm text-slate-600">
          {listing.area != null && <span>{formatArea(listing.area)}</span>}
          {listing.district && <span>{listing.district}</span>}
          {listing.distance_to_ctu != null && (
            <span>{formatDistance(listing.distance_to_ctu)}</span>
          )}
        </div>

        {listing.freshness_label && (
          <p className="text-xs text-slate-400">{listing.freshness_label}</p>
        )}
      </div>
    </Link>
  );
}
