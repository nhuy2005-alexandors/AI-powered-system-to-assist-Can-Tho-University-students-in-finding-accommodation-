"use client";

import { useState } from "react";

export default function ListingGallery({
  images,
  title,
}: {
  images: string[];
  title: string;
}) {
  const [active, setActive] = useState(0);

  if (images.length === 0) {
    return (
      <div className="photo-placeholder flex h-[300px] items-center justify-center rounded-2xl border border-line text-sm font-medium text-ink-faint sm:h-[430px]">
        Tin này chưa có hình ảnh
      </div>
    );
  }

  const showPrevious = () => setActive((current) => (current - 1 + images.length) % images.length);
  const showNext = () => setActive((current) => (current + 1) % images.length);

  return (
    <section aria-label="Hình ảnh phòng trọ">
      <div className="relative overflow-hidden rounded-2xl bg-slate-900">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={images[active]}
          alt={`${title} - ảnh ${active + 1}`}
          className="h-[300px] w-full object-contain sm:h-[430px] lg:h-[510px]"
        />

        {images.length > 1 && (
          <>
            <button
              type="button"
              onClick={showPrevious}
              aria-label="Ảnh trước"
              className="absolute left-4 top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white/95 text-2xl text-ink shadow-lg transition hover:scale-105"
            >
              ‹
            </button>
            <button
              type="button"
              onClick={showNext}
              aria-label="Ảnh tiếp theo"
              className="absolute right-4 top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white/95 text-2xl text-ink shadow-lg transition hover:scale-105"
            >
              ›
            </button>
          </>
        )}

        <span className="absolute bottom-4 right-4 rounded-full bg-slate-950/75 px-3 py-1.5 text-sm font-semibold text-white backdrop-blur">
          {active + 1} / {images.length}
        </span>
      </div>

      {images.length > 1 && (
        <div className="mt-3 flex gap-3 overflow-x-auto pb-1">
          {images.map((src, index) => (
            <button
              key={`${src}-${index}`}
              type="button"
              onClick={() => setActive(index)}
              aria-label={`Xem ảnh ${index + 1}`}
              aria-current={active === index}
              className={`h-[72px] w-[94px] shrink-0 overflow-hidden rounded-xl border-2 transition sm:h-[84px] sm:w-[112px] ${
                active === index
                  ? "border-primary shadow-[0_0_0_2px_rgba(11,77,143,.12)]"
                  : "border-transparent opacity-75 hover:opacity-100"
              }`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={src} alt="" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
