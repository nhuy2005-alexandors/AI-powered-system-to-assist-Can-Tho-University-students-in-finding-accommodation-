async function getApiHealth() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}/health/deps`, { cache: "no-store" });
    return (await res.json()) as Record<string, string>;
  } catch {
    return { api: "unreachable" };
  }
}

export default async function Home() {
  const health = await getApiHealth();

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-3xl font-bold text-slate-800">Trọ CTU</h1>
        <p className="mt-2 text-slate-600">
          Hệ thống tổng hợp &amp; gợi ý nhà trọ AI — Sprint 0 scaffold.
        </p>

        <section className="mt-8 rounded-lg border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-slate-700">
            Backend health
          </h2>
          <ul className="mt-3 space-y-1 font-mono text-sm">
            {Object.entries(health).map(([k, v]) => (
              <li key={k} className="flex justify-between">
                <span className="text-slate-500">{k}</span>
                <span
                  className={
                    v === "ok" || v.includes("POSTGIS") || /^\d/.test(v)
                      ? "text-emerald-600"
                      : "text-rose-600"
                  }
                >
                  {v}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}
