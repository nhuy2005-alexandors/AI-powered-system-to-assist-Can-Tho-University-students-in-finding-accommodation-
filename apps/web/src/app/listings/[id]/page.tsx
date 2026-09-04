import Link from "next/link";
import { notFound } from "next/navigation";
import ListingCard from "@/app/ListingCard";
import SiteHeader from "@/app/SiteHeader";
import { getListing, searchListings, type ApiError, type ListingOut } from "@/lib/api";
import { getCurrentUser } from "@/lib/current-user";
import { formatArea, formatDistance, formatPrice, riskBadge } from "@/lib/format";
import DeleteListingButton from "./DeleteListingButton";
import ListingActions from "./ListingActions";
import ListingGallery from "./ListingGallery";
import ReportButton from "./ReportButton";

export const dynamic = "force-dynamic";

const SOURCE_NAMES: Record<string, string> = {
  user: "Người dùng Trọ CTU",
  dev_seed: "Dữ liệu mẫu đã kiểm tra",
  phongtro123: "Phongtro123",
  tromoi: "Trọ Mới",
  mogi: "Mogi",
  bds123: "BDS123",
  nhadatcantho: "Nhà đất Cần Thơ",
  nhadatcantho247: "Nhà đất Cần Thơ 247",
};

const AMENITIES = [
  { label: "Wi-Fi", keywords: ["wifi", "wi-fi", "internet"] },
  { label: "Có máy lạnh", keywords: ["máy lạnh", "điều hòa"] },
  { label: "Có gác", keywords: ["có gác", "gác lửng"] },
  { label: "Chỗ để xe", keywords: ["để xe", "giữ xe", "bãi xe"] },
  { label: "WC riêng", keywords: ["wc riêng", "vệ sinh riêng", "toilet riêng"] },
  { label: "Giờ giấc tự do", keywords: ["giờ tự do", "giờ giấc tự do", "không chung chủ"] },
  { label: "Cho nuôi thú cưng", keywords: ["nuôi thú cưng", "cho nuôi pet", "pet friendly"] },
];

function sourceName(source: string): string {
  return SOURCE_NAMES[source.toLowerCase()] ?? source;
}

function amenitiesFrom(listing: ListingOut): string[] {
  const content = `${listing.title} ${listing.description ?? ""}`.toLocaleLowerCase("vi");
  return AMENITIES.filter((item) => item.keywords.some((keyword) => content.includes(keyword))).map(
    (item) => item.label,
  );
}

function mapEmbedUrl(lat: number, lng: number): string {
  const delta = 0.006;
  const bbox = [lng - delta, lat - delta, lng + delta, lat + delta].join(",");
  return `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik&marker=${lat},${lng}`;
}

function mapUrl(lat: number, lng: number): string {
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}`;
}

export default async function ListingDetailPage({ params }: { params: { id: string } }) {
  let listing: ListingOut;
  try {
    listing = await getListing(params.id);
  } catch (error) {
    if ((error as ApiError).status === 404) notFound();
    throw error;
  }

  const [user, similarResult] = await Promise.all([
    getCurrentUser(),
    searchListings({ district: listing.district ?? undefined, page: 1, size: 6, sort: "newest" }).catch(
      () => null,
    ),
  ]);

  const canManage = Boolean(user) && (
    user?.role === "admin" || (listing.source === "user" && listing.posted_by === user?.id)
  );
  const canReport = Boolean(user) && listing.posted_by !== user?.id;
  const badge = riskBadge(listing.risk_level);
  const amenities = amenitiesFrom(listing);
  const similar = (similarResult?.items ?? []).filter((item) => item.id !== listing.id).slice(0, 4);
  const source = sourceName(listing.source);
  const locationLabel = listing.address || listing.district || "Cần Thơ";
  const routeTimes = listing.route_time_campus ?? [];
  const campusNames = ["CTU khu I", "CTU khu II", "CTU khu III"];

  return (
    <div className="min-h-screen bg-paper">
      <div className="bg-navy px-5 py-2 text-[12.5px] text-[#b9d3ec] sm:px-10">
        Sản phẩm nghiên cứu khoa học sinh viên · Trường Công nghệ Thông tin &amp; Truyền thông,
        ĐH Cần Thơ
      </div>
      <SiteHeader />

      <main className="mx-auto max-w-[1240px] px-4 py-6 sm:px-8 lg:px-10 lg:py-8">
        <nav aria-label="Điều hướng" className="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
          <Link href="/" className="hover:text-primary">Tìm trọ</Link>
          <span aria-hidden="true">›</span>
          {listing.district && (
            <>
              <Link href={`/?district=${encodeURIComponent(listing.district)}`} className="hover:text-primary">
                {listing.district}
              </Link>
              <span aria-hidden="true">›</span>
            </>
          )}
          <span className="max-w-[52ch] truncate font-medium text-ink">{listing.title}</span>
        </nav>

        <div className="mt-5 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_350px]">
          <div className="min-w-0 rounded-[22px] border border-line bg-white p-3 shadow-[0_12px_35px_-28px_rgba(6,48,92,.55)] sm:p-5">
            <ListingGallery images={listing.images} title={listing.title} />
          </div>

          <aside className="rounded-[22px] border border-line bg-white p-5 shadow-[0_12px_35px_-26px_rgba(6,48,92,.55)] lg:sticky lg:top-5 lg:p-6">
            <p className="text-sm font-medium text-ink-muted">Giá thuê</p>
            <p className="mt-1 text-[30px] font-extrabold tracking-[-0.03em] text-primary">
              {formatPrice(listing.price)}
            </p>
            {listing.area != null && listing.price != null && (
              <p className="mt-1 text-sm text-ink-muted">
                Khoảng {Math.round(listing.price / listing.area).toLocaleString("vi-VN")} đ/m²
              </p>
            )}

            <div className="mt-5">
              <ListingActions
                listingId={listing.id}
                loggedIn={Boolean(user)}
                sourceUrl={listing.source_url}
              />
            </div>

            <div className="mt-5 border-t border-line-soft pt-5">
              <p className="text-xs font-semibold uppercase tracking-[.08em] text-ink-faint">Đăng bởi</p>
              <div className="mt-3 flex items-center gap-3">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-primary-soft text-base font-extrabold text-primary">
                  {source.trim().charAt(0).toUpperCase() || "T"}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-[15px] font-bold text-ink">{source}</p>
                  <p className="mt-0.5 text-xs text-ink-muted">
                    {listing.source === "user" ? "Tin do cộng đồng đăng" : "Tin được hệ thống tổng hợp"}
                  </p>
                </div>
              </div>
            </div>

            <Link
              href="/chat"
              className="mt-5 block rounded-2xl border border-primary-ring bg-primary-soft p-4 transition hover:border-primary/40"
            >
              <span className="text-[15px] font-bold text-navy">Hỏi trợ lý về phòng này</span>
              <span className="mt-1 block text-sm leading-relaxed text-[#12507f]">
                Kiểm tra giá, hợp đồng, khoảng cách và các dấu hiệu cần lưu ý.
              </span>
              <span className="mt-2 inline-block text-sm font-semibold text-primary-bright">Mở trợ lý AI →</span>
            </Link>
          </aside>
        </div>

        <div className="mt-6 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_350px]">
          <article className="min-w-0 space-y-5">
            <section id="tong-quan" className="scroll-mt-4 rounded-[20px] border border-line bg-white p-5 sm:p-7">
              <div className="flex flex-wrap gap-2">
                <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${badge.className}`}>
                  {badge.label}
                </span>
                {listing.freshness_label && (
                  <span className="rounded-full bg-tint px-3 py-1.5 text-xs font-semibold text-ink-soft">
                    {listing.freshness_label}
                  </span>
                )}
                <span className="rounded-full bg-tint px-3 py-1.5 text-xs font-semibold text-ink-soft">
                  Nguồn: {source}
                </span>
              </div>

              <h1 className="mt-4 text-balance text-[26px] font-extrabold leading-tight tracking-[-0.025em] text-ink sm:text-[34px]">
                {listing.title}
              </h1>
              <p className="mt-3 flex items-start gap-2 text-[15px] leading-relaxed text-ink-soft sm:text-base">
                <span aria-hidden="true">⌖</span>
                <span>{locationLabel}</span>
              </p>

              <nav className="mt-6 flex gap-1 overflow-x-auto border-b border-line-soft" aria-label="Các phần của tin">
                {[
                  ["#tong-quan", "Tổng quan"],
                  ["#dac-diem", "Đặc điểm"],
                  ["#mo-ta", "Mô tả"],
                  ["#vi-tri", "Vị trí"],
                  ["#phan-hoi", "Phản hồi"],
                ].map(([href, label]) => (
                  <a
                    key={href}
                    href={href}
                    className="shrink-0 border-b-2 border-transparent px-3 py-3 text-sm font-semibold text-ink-muted transition hover:border-primary hover:text-primary"
                  >
                    {label}
                  </a>
                ))}
              </nav>

              <div id="dac-diem" className="scroll-mt-4 pt-6">
                <h2 className="text-xl font-bold text-ink">Đặc điểm phòng trọ</h2>
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Fact label="Giá thuê" value={formatPrice(listing.price)} />
                  <Fact label="Diện tích" value={listing.area != null ? formatArea(listing.area) : "Chưa rõ"} />
                  <Fact label="Khu vực" value={listing.district || "Cần Thơ"} />
                  <Fact
                    label="Cách CTU"
                    value={listing.distance_to_ctu != null ? formatDistance(listing.distance_to_ctu).replace("cách CTU ", "") : "Chưa rõ"}
                  />
                </div>

                {amenities.length > 0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {amenities.map((amenity) => (
                      <span key={amenity} className="rounded-xl border border-line bg-tint px-3 py-2 text-sm font-medium text-ink-soft">
                        ✓ {amenity}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </section>

            {routeTimes.length > 0 && (
              <section className="rounded-[20px] border border-line bg-white p-5 sm:p-7">
                <div className="flex flex-wrap items-end justify-between gap-2">
                  <h2 className="text-xl font-bold text-ink">Thời gian đi xe máy tới trường</h2>
                  <p className="text-xs text-ink-muted">Tính theo dữ liệu đường thực tế</p>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  {routeTimes.slice(0, 3).map((minutes, index) => (
                    <div key={campusNames[index]} className="flex items-center justify-between rounded-2xl border border-line-soft bg-slate-50 p-4">
                      <div>
                        <p className="font-semibold text-ink">{campusNames[index]}</p>
                        <p className="mt-0.5 text-xs text-ink-muted">Bằng xe máy</p>
                      </div>
                      <p className="text-2xl font-extrabold text-primary">{Math.round(minutes)}<span className="ml-1 text-xs font-medium">phút</span></p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section id="mo-ta" className="scroll-mt-4 rounded-[20px] border border-line bg-white p-5 sm:p-7">
              <h2 className="text-xl font-bold text-ink">Mô tả chi tiết</h2>
              {listing.description ? (
                <p className="mt-4 whitespace-pre-line text-[15.5px] leading-7 text-ink-soft">{listing.description}</p>
              ) : (
                <p className="mt-4 text-sm text-ink-muted">Người đăng chưa bổ sung mô tả cho tin này.</p>
              )}
            </section>

            {(listing.lat != null || listing.address) && (
              <section id="vi-tri" className="scroll-mt-4 overflow-hidden rounded-[20px] border border-line bg-white">
                <div className="p-5 sm:p-7">
                  <h2 className="text-xl font-bold text-ink">Địa chỉ &amp; vị trí</h2>
                  <p className="mt-2 text-[15px] text-ink-soft">{locationLabel}</p>
                  <p className="mt-1 text-xs text-ink-muted">
                    Vị trí bản đồ có thể là vị trí tương đối; hãy xác nhận với người đăng trước khi đi xem.
                  </p>
                </div>
                {listing.lat != null && listing.lng != null && (
                  <>
                    <iframe
                      title={`Bản đồ ${listing.title}`}
                      src={mapEmbedUrl(listing.lat, listing.lng)}
                      className="h-[280px] w-full border-0"
                      loading="lazy"
                    />
                    <a
                      href={mapUrl(listing.lat, listing.lng)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block border-t border-line-soft px-5 py-3 text-right text-sm font-semibold text-primary-bright hover:bg-tint"
                    >
                      Mở bản đồ lớn ↗
                    </a>
                  </>
                )}
              </section>
            )}

            <section className="rounded-[20px] border border-amber-200 bg-amber-50 p-5 sm:p-6">
              <div className="flex gap-3">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-amber-600 font-bold text-white">!</span>
                <div>
                  <h2 className="font-bold text-amber-950">Trước khi đặt cọc, hãy đi xem phòng</h2>
                  <p className="mt-1.5 text-sm leading-6 text-amber-900">
                    Không chuyển tiền khi chưa gặp người cho thuê và chưa xem hợp đồng. Kiểm tra kỹ giá điện,
                    nước, tiền cọc và tình trạng phòng thực tế.
                  </p>
                </div>
              </div>
            </section>

            <section id="phan-hoi" className="scroll-mt-4 rounded-[20px] border border-line bg-white p-5 sm:p-7">
              <h2 className="text-xl font-bold text-ink">Phản hồi cộng đồng</h2>
              <p className="mt-2 text-sm leading-6 text-ink-muted">
                Góp ý của bạn giúp hệ thống phát hiện tin sai, tin đã hết hoặc dấu hiệu lừa đảo. Nội dung phản hồi
                chỉ được gửi tới quản trị viên để kiểm tra.
              </p>

              {listing.risk_reasons.length > 0 && (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                  <p className="text-sm font-bold text-amber-950">Các điểm hệ thống lưu ý</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
                    {listing.risk_reasons.map((reason) => <li key={reason}>{reason}</li>)}
                  </ul>
                </div>
              )}

              {listing.report_count > 0 && (
                <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
                  Tin này có {listing.report_count} phản hồi chưa bị bác bỏ từ cộng đồng.
                </p>
              )}

              <div className="mt-4">
                <ReportButton listingId={listing.id} loggedIn={Boolean(user)} canReport={canReport} />
              </div>
            </section>

            {canManage && (
              <section className="rounded-[20px] border border-line bg-white p-5 sm:p-6">
                <h2 className="font-bold text-ink">Quản lý tin</h2>
                <div className="mt-3 flex flex-wrap gap-3">
                  <Link href={`/listings/${listing.id}/edit`} className="rounded-xl border border-line px-4 py-2.5 text-sm font-semibold text-ink-soft hover:bg-tint">
                    Sửa thông tin
                  </Link>
                  <DeleteListingButton id={listing.id} />
                </div>
              </section>
            )}
          </article>

          <aside className="hidden rounded-[20px] border border-line bg-white p-5 lg:block">
            <p className="text-xs font-semibold uppercase tracking-[.08em] text-ink-faint">Độ tin cậy dữ liệu</p>
            <div className="mt-4 space-y-4">
              <DataScore label="Chất lượng tin" value={listing.quality_score} />
              <DataScore label="Độ mới dữ liệu" value={listing.freshness_score} />
            </div>
            <p className="mt-4 text-xs leading-5 text-ink-muted">
              Điểm số hỗ trợ sàng lọc và không thay thế việc xem phòng, xác minh người đăng.
            </p>
          </aside>
        </div>

        {similar.length > 0 && (
          <section className="mt-7 rounded-[22px] border border-line bg-white p-5 sm:p-7">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-[22px] font-bold text-ink">Tin đăng tương tự</h2>
                <p className="mt-1 text-sm text-ink-muted">
                  {listing.district ? `Các phòng khác tại ${listing.district}` : "Các phòng mới cập nhật"}
                </p>
              </div>
              <Link href={listing.district ? `/?district=${encodeURIComponent(listing.district)}` : "/"} className="text-sm font-semibold text-primary-bright hover:underline">
                Xem tất cả →
              </Link>
            </div>
            <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {similar.map((item) => <ListingCard key={item.id} listing={item} />)}
            </div>
          </section>
        )}
      </main>

      <footer className="mt-8 bg-navy px-5 py-8 text-[13.5px] text-[#a9c7e4] sm:px-10">
        <div className="mx-auto flex max-w-[1160px] flex-wrap items-center justify-between gap-3">
          <span>Trọ CTU · Đề tài NCKH sinh viên 2026 · Trường CNTT&amp;TT, ĐH Cần Thơ</span>
          <span className="flex gap-6">
            <Link href="/map" className="transition hover:text-white">Bản đồ</Link>
            <Link href="/listings/new" className="transition hover:text-white">Đăng tin</Link>
          </span>
        </div>
      </footer>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-slate-50 p-4">
      <p className="text-xs font-medium text-ink-muted">{label}</p>
      <p className="mt-1.5 break-words text-[17px] font-bold leading-snug text-ink">{value}</p>
    </div>
  );
}

function DataScore({ label, value }: { label: string; value: number | null }) {
  const percent = value == null ? null : Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div>
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="font-medium text-ink-soft">{label}</span>
        <span className="font-bold text-ink">{percent == null ? "Chưa có" : `${percent}%`}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-line-soft">
        <div className="h-full rounded-full bg-primary" style={{ width: `${percent ?? 0}%` }} />
      </div>
    </div>
  );
}
