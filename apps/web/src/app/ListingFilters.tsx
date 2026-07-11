"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

const DISTRICTS = [
  "Ninh Kiều",
  "Bình Thủy",
  "Cái Răng",
  "Ô Môn",
  "Thốt Nốt",
  "Phong Điền",
];

const SORT_OPTIONS = [
  { value: "newest", label: "Mới nhất" },
  { value: "price_asc", label: "Giá thấp → cao" },
  { value: "price_desc", label: "Giá cao → thấp" },
  { value: "nearest", label: "Gần CTU nhất" },
  { value: "quality", label: "Chất lượng" },
];

export type ListingFiltersValues = {
  q?: string;
  district?: string;
  min_price?: string;
  max_price?: string;
  min_area?: string;
  sort?: string;
};

// Nhận initial values từ server component (searchParams) — không tự đọc
// useSearchParams ở đây để tránh phải bọc Suspense.
export default function ListingFilters({ initial }: { initial: ListingFiltersValues }) {
  const router = useRouter();
  const [values, setValues] = useState<ListingFiltersValues>(initial);

  const update = (patch: Partial<ListingFiltersValues>) =>
    setValues((prev) => ({ ...prev, ...patch }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (values.q) params.set("q", values.q);
    if (values.district) params.set("district", values.district);
    if (values.min_price) params.set("min_price", values.min_price);
    if (values.max_price) params.set("max_price", values.max_price);
    if (values.min_area) params.set("min_area", values.min_area);
    if (values.sort && values.sort !== "newest") params.set("sort", values.sort);
    router.push(`/?${params.toString()}`);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-6"
    >
      <div className="lg:col-span-2">
        <label htmlFor="q" className="block text-sm font-medium text-slate-700">
          Tìm kiếm
        </label>
        <input
          id="q"
          type="text"
          placeholder="Tên phòng, địa chỉ..."
          value={values.q ?? ""}
          onChange={(e) => update({ q: e.target.value })}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-slate-800 focus:border-emerald-500 focus:outline-none"
        />
      </div>

      <div>
        <label htmlFor="district" className="block text-sm font-medium text-slate-700">
          Quận/huyện
        </label>
        <select
          id="district"
          value={values.district ?? ""}
          onChange={(e) => update({ district: e.target.value })}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-slate-800 focus:border-emerald-500 focus:outline-none"
        >
          <option value="">Tất cả</option>
          {DISTRICTS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="min_price" className="block text-sm font-medium text-slate-700">
          Giá từ (VND)
        </label>
        <input
          id="min_price"
          type="number"
          min={0}
          value={values.min_price ?? ""}
          onChange={(e) => update({ min_price: e.target.value })}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-slate-800 focus:border-emerald-500 focus:outline-none"
        />
      </div>

      <div>
        <label htmlFor="max_price" className="block text-sm font-medium text-slate-700">
          Giá đến (VND)
        </label>
        <input
          id="max_price"
          type="number"
          min={0}
          value={values.max_price ?? ""}
          onChange={(e) => update({ max_price: e.target.value })}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-slate-800 focus:border-emerald-500 focus:outline-none"
        />
      </div>

      <div>
        <label htmlFor="min_area" className="block text-sm font-medium text-slate-700">
          DT tối thiểu (m²)
        </label>
        <input
          id="min_area"
          type="number"
          min={0}
          value={values.min_area ?? ""}
          onChange={(e) => update({ min_area: e.target.value })}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-slate-800 focus:border-emerald-500 focus:outline-none"
        />
      </div>

      <div>
        <label htmlFor="sort" className="block text-sm font-medium text-slate-700">
          Sắp xếp
        </label>
        <select
          id="sort"
          value={values.sort ?? "newest"}
          onChange={(e) => update({ sort: e.target.value })}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-slate-800 focus:border-emerald-500 focus:outline-none"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-end lg:col-span-6">
        <button
          type="submit"
          className="rounded bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700"
        >
          Lọc kết quả
        </button>
      </div>
    </form>
  );
}
