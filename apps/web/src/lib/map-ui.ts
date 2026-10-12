import type * as L from "leaflet";

export type PriceOrder = "original" | "price_asc" | "price_desc";

function pinIcon(leaflet: typeof import("leaflet"), selected: boolean): L.DivIcon {
  const size = selected ? 32 : 22;
  const height = Math.round(size * 1.3);
  const color = selected ? "#0f766e" : "#e11d48";
  return leaflet.divIcon({
    className: "",
    html: `<svg width="${size}" height="${height}" viewBox="0 0 24 32" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 0C5.4 0 0 5.4 0 12c0 8.4 12 20 12 20s12-11.6 12-20C24 5.4 18.6 0 12 0z"
        fill="${color}" stroke="${selected ? "#ffffff" : "rgba(0,0,0,.15)"}" stroke-width="${selected ? 2.5 : 1}"/>
      <circle cx="12" cy="12" r="4.2" fill="#ffffff"/>
    </svg>`,
    iconSize: [size, height],
    iconAnchor: [size / 2, height],
    popupAnchor: [0, -height + 4],
  });
}

export function createHousingIcon(
  leaflet: typeof import("leaflet"),
  selected: boolean,
): L.DivIcon {
  return pinIcon(leaflet, selected);
}

export function createCampusIcon(leaflet: typeof import("leaflet")): L.DivIcon {
  return leaflet.divIcon({
    className: "",
    html: `<svg width="26" height="26" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="11" fill="#1d4ed8" stroke="#ffffff" stroke-width="2"/>
      <path d="M12 6l1.8 3.9 4.2.5-3.1 2.9.8 4.2L12 15.4 8.3 17.5l.8-4.2L6 10.4l4.2-.5z" fill="#fde047"/>
    </svg>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

export function normalizeMapSearch(value: string | null | undefined): string {
  return (value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/đ/g, "d");
}

export function sortMapListingsByPrice<
  T extends { id: number; price: number | null },
>(rows: readonly T[], order: PriceOrder): T[] {
  if (order === "original") return [...rows];

  return [...rows].sort((left, right) => {
    if (left.price === null) return right.price === null ? left.id - right.id : 1;
    if (right.price === null) return -1;

    const priceOrder = order === "price_asc"
      ? left.price - right.price
      : right.price - left.price;
    return priceOrder || left.id - right.id;
  });
}

export function focusSelectedPosition(
  map: Pick<L.Map, "flyTo" | "getZoom">,
  position: L.LatLngTuple | null,
): void {
  if (!position) return;
  map.flyTo(position, Math.max(map.getZoom(), 16), { duration: 0.6 });
}

export function observeMapResize(
  map: Pick<L.Map, "getContainer" | "invalidateSize">,
): () => void {
  const observer = new ResizeObserver(() => map.invalidateSize());
  observer.observe(map.getContainer());
  return () => observer.disconnect();
}

export function scrollMapSelection(
  container: HTMLElement | null,
  listingId: number | null,
): void {
  if (!container || listingId === null) return;
  const row = container.querySelector<HTMLElement>(`[data-listing-id="${listingId}"]`);
  row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
}
