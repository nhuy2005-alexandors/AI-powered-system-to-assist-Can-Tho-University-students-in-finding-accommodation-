import type { MobilityMapConfig } from "@/lib/config";
import { mobilityMapConfig } from "@/lib/config";
import MobilityWorkspace from "@/components/mobility/MobilityWorkspace";

export const dynamic = "force-dynamic";

export default function MapPage() {
  if (process.env.MOBILITY_ENABLED === "true") {
    const mapConfig: MobilityMapConfig = mobilityMapConfig();
    return <MobilityWorkspace mapConfig={mapConfig} />;
  }

  return (
    <main
      data-testid="mobility-map-unavailable"
      className="grid min-h-[50vh] place-items-center bg-slate-50 px-6 text-center text-slate-800"
    >
      <section className="max-w-lg rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold">Bản đồ di chuyển hiện chưa khả dụng</h1>
        <p className="mt-3 text-sm text-slate-600">
          Danh sách chỗ ở và bản đồ chưa được bật trong môi trường này.
        </p>
      </section>
    </main>
  );
}
