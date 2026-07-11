import Link from "next/link";
import { searchListings, type ApiError } from "@/lib/api";
import ListingCard from "./ListingCard";
import ListingFilters from "./ListingFilters";

export const dynamic = "force-dynamic";

type SearchParamsShape = {
  q?: string;
  district?: string;
  min_price?: string;
  max_price?: string;
  min_area?: string;
  sort?: string;
  page?: string;
};

export default async function Home({
  searchParams,
}: {
  searchParams: SearchParamsShape;
}) {
  const page = Math.max(1, Number(searchParams.page) || 1);
  const size = 20;

  let result;
  let errorMessage: string | null = null;
  try {
    result = await searchListings({
      q: searchParams.q,
      district: searchParams.district,
      min_price: searchParams.min_price ? Number(searchParams.min_price) : undefined,
      max_price: searchParams.max_price ? Number(searchParams.max_price) : undefined,
      min_area: searchParams.min_area ? Number(searchParams.min_area) : undefined,
      sort: searchParams.sort,
      page,
      size,
    });
  } catch (e) {
    errorMessage = (e as ApiError).detail ?? "Không thể tải danh sách tin";
    result = { total: 0, page, size, items: [] };
  }

  const totalPages = Math.max(1, Math.ceil(result.total / size));

  return (
    <main className="min-h-screen bg-slate-50 p-4 sm:p-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-slate-800">Trọ CTU</h1>
            <p className="mt-1 text-slate-600">Tìm phòng trọ gần ĐH Cần Thơ</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/map"
              className="rounded border border-slate-300 px-4 py-2 font-medium text-slate-700 hover:bg-slate-100"
            >
              Xem bản đồ
            </Link>
            <Link
              href="/listings/new"
              className="rounded bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700"
            >
              Đăng tin
            </Link>
          </div>
        </div>

        <div className="mt-6">
          <ListingFilters
            initial={{
              q: searchParams.q,
              district: searchParams.district,
              min_price: searchParams.min_price,
              max_price: searchParams.max_price,
              min_area: searchParams.min_area,
              sort: searchParams.sort,
            }}
          />
        </div>

        {errorMessage && (
          <p className="mt-6 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-600">
            {errorMessage}
          </p>
        )}

        {!errorMessage && result.items.length === 0 && (
          <p className="mt-10 text-center text-slate-500">Không tìm thấy tin phù hợp</p>
        )}

        {result.items.length > 0 && (
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {result.items.map((listing) => (
              <ListingCard key={listing.id} listing={listing} />
            ))}
          </div>
        )}

        {result.total > 0 && (
          <div className="mt-8 flex items-center justify-center gap-4">
            <PageLink
              searchParams={searchParams}
              page={page - 1}
              disabled={page <= 1}
              label="Trước"
            />
            <span className="text-sm text-slate-600">
              Trang {page} / {totalPages}
            </span>
            <PageLink
              searchParams={searchParams}
              page={page + 1}
              disabled={page >= totalPages}
              label="Sau"
            />
          </div>
        )}
      </div>
    </main>
  );
}

function PageLink({
  searchParams,
  page,
  disabled,
  label,
}: {
  searchParams: SearchParamsShape;
  page: number;
  disabled: boolean;
  label: string;
}) {
  if (disabled) {
    return (
      <span className="cursor-not-allowed rounded border border-slate-200 px-4 py-2 text-sm text-slate-400">
        {label}
      </span>
    );
  }

  const params = new URLSearchParams();
  Object.entries(searchParams).forEach(([key, value]) => {
    if (value && key !== "page") params.set(key, value);
  });
  params.set("page", String(page));

  return (
    <Link
      href={`/?${params.toString()}`}
      className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
    >
      {label}
    </Link>
  );
}
