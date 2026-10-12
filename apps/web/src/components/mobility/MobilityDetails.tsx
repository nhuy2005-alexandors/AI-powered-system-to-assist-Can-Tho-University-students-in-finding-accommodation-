import type { CatalogListing } from "@/lib/mobility-contracts";
import { formatPrice, safeHttpUrl } from "./mobility-format";

function normalized(value: string | null): string {
  return (value ?? "").trim().toLowerCase().replace(/[ -]+/g, "_");
}

function housingType(value: string | null): string {
  const known: Record<string, string> = {
    room: "Phòng trọ",
    mini_house: "Nhà nhỏ",
    studio: "Căn hộ studio",
    apartment: "Căn hộ",
    whole_house: "Nhà nguyên căn",
  };
  return value ? known[normalized(value)] ?? value : "Loại chỗ ở chưa xác định";
}

function offerKind(value: string | null): { label: string; isTransfer: boolean } {
  const key = normalized(value);
  if (["lease_transfer", "transfer", "handover", "sang_nhuong"].includes(key)) {
    return { label: "Sang nhượng hoặc chuyển giao hợp đồng thuê", isTransfer: true };
  }
  if (["rent", "rental", "for_rent", "cho_thue"].includes(key)) {
    return { label: "Cho thuê", isTransfer: false };
  }
  if (!key || key === "unknown") {
    return { label: "Loại giao dịch chưa xác định", isTransfer: false };
  }
  return { label: value ?? "Loại giao dịch chưa xác định", isTransfer: false };
}

export default function MobilityDetails({ listing }: { listing: CatalogListing }) {
  const safeSource = safeHttpUrl(listing.source_url);
  const safeContact = safeHttpUrl(listing.source_contact_url);
  const offer = offerKind(listing.offer_kind);
  const descriptionPartial =
    listing.description_is_partial === true ||
    listing.description_state?.toUpperCase() === "PARTIAL" ||
    listing.description_completeness?.toUpperCase() === "PARTIAL";
  const descriptionUnknown =
    listing.description_is_partial == null &&
    listing.description_state == null &&
    listing.description_completeness == null;

  return (
    <section aria-label="Chi tiết tin được chọn" className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">{listing.title}</h2>
        <p className="mt-1 text-sm font-semibold text-emerald-800">{formatPrice(listing.price)}</p>
        <p className="mt-1 text-sm text-slate-600">{listing.area == null ? "Diện tích chưa rõ" : `${listing.area} m²`}</p>
        {listing.address && <p className="mt-1 text-sm text-slate-600">{listing.address}</p>}
        {safeSource && (
          <a
            href={safeSource}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Xem tin gốc
          </a>
        )}
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-700">
          {listing.unit_type_uncertain !== false || listing.housing_type == null
            ? "Loại chỗ ở chưa xác định"
            : housingType(listing.housing_type)}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-700">
          {offer.label}
        </span>
        {descriptionPartial && (
          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-900">
            Mô tả chưa đầy đủ
          </span>
        )}
        {descriptionUnknown && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-700">
            Mức độ mô tả chưa rõ
          </span>
        )}
        {offer.isTransfer && listing.lease_transfer_terms_verified !== true && (
          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-900">
            Điều kiện thuê hoặc sang nhượng chưa xác minh
          </span>
        )}
        {!offer.isTransfer && listing.offer_context_uncertain !== false && (
          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-900">
            Ngữ cảnh giao dịch chưa rõ
          </span>
        )}
        {listing.mixed_use_possible === true && (
          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-900">
            Có thể kết hợp ở với mục đích khác
          </span>
        )}
      </div>

      <div className="rounded-lg bg-slate-50 p-3">
        <h3 className="text-sm font-medium text-slate-800">Vị trí</h3>
        {listing.position == null ? (
          <p className="mt-1 text-sm text-amber-900">
            Tin chưa có tọa độ; vẫn giữ trong danh sách nhưng không đặt ghim.
          </p>
        ) : listing.position.precision === "APPROXIMATE" ? (
          <p className="mt-1 text-sm text-amber-900">
            Vị trí trên sơ đồ chỉ gần đúng; cần xác nhận địa điểm và lối vào.
          </p>
        ) : listing.position.precision === "VERIFIED" ? (
          <p className="mt-1 text-sm text-slate-600">Tọa độ có nguồn xác minh.</p>
        ) : (
          <p className="mt-1 text-sm text-amber-900">Vị trí chưa được xác minh.</p>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 p-3">
        <h3 className="text-sm font-medium text-slate-800">Mô tả từ tin đăng</h3>
        <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-600">
          {listing.description || "Tin đăng chưa có mô tả."}
        </p>
      </div>

      {safeContact && (
        <a
          href={safeContact}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex rounded-md border border-emerald-700 px-3 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-50"
        >
          Liên hệ nguồn tin
        </a>
      )}
    </section>
  );
}
