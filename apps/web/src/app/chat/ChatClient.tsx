"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

type Source = {
  listing_id: number;
  rank: number;
  similarity_score: number;
  title: string;
  source: string;
  source_url: string | null;
};

type Listing = {
  id: number;
  title: string;
  price: number | null;
  area: number | null;
  address: string | null;
  district: string | null;
  amenities: Record<string, unknown>;
  distance_to_ctu: number | null;
  route_time_campus: number[] | null;
  source_url: string | null;
  similarity_score: number;
  vector_score: number;
  bm25_score: number;
  rank: number;
  match_reasons: string[];
};

type Turn = {
  key: string;
  role: "user" | "assistant";
  content: string;
  listings?: Listing[];
  sources?: Source[];
  degraded?: boolean;
  generationProvider?: string;
  generationModel?: string | null;
};

type AskResponse = {
  answer: string;
  listings: Listing[];
  sources: Source[];
  degraded: boolean;
  degraded_reasons: string[];
  retrieval_mode: string;
  generation_provider: string;
  generation_model: string | null;
  latency_ms: number;
};

type WidgetMode = "closed" | "compact" | "expanded";

const WELCOME: Turn = {
  key: "welcome",
  role: "assistant",
  content:
    "Chào bạn! Mình là Trợ lý Trọ CTU. Hãy cho mình biết ngân sách, khu vực, khoảng cách đến trường hoặc tiện ích bạn cần nhé.",
};

const QUICK_PROMPTS = [
  "Phòng dưới 2 triệu gần CTU",
  "Ở Ninh Kiều, có máy lạnh và wifi",
  "Phòng nữ, cách trường dưới 2 km",
];

const amenityLabels: Record<string, string> = {
  wifi: "Wi-Fi",
  air_conditioner: "Máy lạnh",
  mezzanine: "Có gác",
  parking: "Chỗ để xe",
  private_bathroom: "WC riêng",
  refrigerator: "Tủ lạnh",
  washing_machine: "Máy giặt",
  kitchen: "Bếp",
  pets_allowed: "Nuôi thú cưng",
  flexible_hours: "Giờ tự do",
};

function money(value: number | null) {
  return value == null
    ? "Chưa có giá"
    : new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND",
        maximumFractionDigits: 0,
      }).format(value);
}

function distance(value: number | null) {
  if (value == null) return null;
  return value >= 1000 ? `${(value / 1000).toFixed(1)} km đến CTU` : `${Math.round(value)} m đến CTU`;
}

function providerLabel(provider?: string, model?: string | null) {
  if (!provider) return null;
  if (provider === "qwen-local") return `Qwen local${model ? ` · ${model}` : ""}`;
  if (provider === "gemini") return `Gemini${model ? ` · ${model}` : ""}`;
  if (provider === "template") return "Mẫu trả lời an toàn";
  if (provider === "rule") return "Bộ phân loại yêu cầu";
  return provider;
}

function Icon({ name }: { name: "chat" | "expand" | "shrink" | "close" | "send" | "reset" }) {
  const paths = {
    chat: <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z" />,
    expand: <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />,
    shrink: <path d="M4 14h6v6M20 10h-6V4M10 14l-7 7M14 10l7-7" />,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    send: <path d="m22 2-7 20-4-9-9-4 20-7ZM11 13 22 2" />,
    reset: <path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5" />,
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      {paths[name]}
    </svg>
  );
}

export default function ChatClient() {
  const pathname = usePathname();
  const [mode, setMode] = useState<WidgetMode>("closed");
  const [turns, setTurns] = useState<Turn[]>([WELCOME]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (pathname === "/chat") setMode("compact");
  }, [pathname]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  useEffect(() => {
    if (mode !== "closed") window.setTimeout(() => inputRef.current?.focus(), 180);
  }, [mode]);

  async function send(text: string) {
    const cleanText = text.trim();
    if (cleanText.length < 2 || loading) return;
    setMessage("");
    setError(null);
    setLoading(true);
    setTurns((items) => [
      ...items,
      { key: `user-${Date.now()}`, role: "user", content: cleanText },
    ]);
    try {
      const response = await fetch("/api/chat/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: cleanText }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Không thể gửi câu hỏi");
      const result = body as AskResponse;
      setTurns((items) => [
        ...items,
        {
          key: `assistant-${Date.now()}`,
          role: "assistant",
          content: result.answer,
          listings: result.listings,
          sources: result.sources,
          degraded: result.degraded,
          generationProvider: result.generation_provider,
          generationModel: result.generation_model,
        },
      ]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Đã có lỗi xảy ra");
    } finally {
      setLoading(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void send(message);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(message);
    }
  }

  function resetConversation() {
    setTurns([WELCOME]);
    setError(null);
    setMessage("");
  }

  // Admin có giao diện quản trị riêng; không hiển thị widget nổi che bảng dữ liệu.
  if (pathname.startsWith("/admin")) return null;

  if (mode === "closed") {
    return (
      <button
        type="button"
        onClick={() => setMode("compact")}
        className="group fixed bottom-5 right-5 z-50 flex items-center gap-3 rounded-full bg-[#005baa] p-3.5 text-white shadow-[0_12px_35px_rgba(0,74,143,0.38)] transition hover:-translate-y-1 hover:bg-[#004a8f] focus:outline-none focus:ring-4 focus:ring-blue-200 sm:px-5"
        aria-label="Mở Trợ lý Trọ CTU"
      >
        <span className="relative grid h-7 w-7 place-items-center">
          <Icon name="chat" />
          <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-[#005baa] bg-emerald-400" />
        </span>
        <span className="hidden text-sm font-semibold sm:inline">Trợ lý Trọ CTU</span>
      </button>
    );
  }

  const expanded = mode === "expanded";
  return (
    <section
      aria-label="Trợ lý tìm nhà trọ CTU"
      className={`fixed z-50 flex overflow-hidden border border-blue-100 bg-white shadow-[0_24px_70px_rgba(15,45,80,0.28)] transition-all duration-300 ${
        expanded
          ? "inset-0 rounded-none sm:inset-5 sm:rounded-3xl"
          : "bottom-3 right-3 h-[min(680px,calc(100vh-1.5rem))] w-[min(400px,calc(100vw-1.5rem))] rounded-3xl"
      }`}
    >
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="relative overflow-hidden bg-gradient-to-br from-[#0068b7] via-[#005baa] to-[#003f7d] px-4 py-3.5 text-white">
          <div className="absolute -right-10 -top-14 h-36 w-36 rounded-full border border-white/10 bg-white/5" />
          <div className="relative flex items-center gap-3">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-white text-[#005baa] shadow-sm">
              <span className="text-xl font-black">CTU</span>
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="truncate font-bold">Trợ lý Trọ CTU</h2>
              <p className="flex items-center gap-1.5 text-xs text-blue-100">
                <span className="h-2 w-2 rounded-full bg-emerald-300" />
                Qwen local · Gemini tùy chọn · Không lưu lịch sử
              </p>
            </div>
            <button type="button" onClick={resetConversation} title="Cuộc trò chuyện mới" className="rounded-xl p-2 text-blue-100 transition hover:bg-white/15 hover:text-white">
              <Icon name="reset" />
            </button>
            <button type="button" onClick={() => setMode(expanded ? "compact" : "expanded")} title={expanded ? "Thu nhỏ" : "Phóng to"} className="rounded-xl p-2 text-blue-100 transition hover:bg-white/15 hover:text-white">
              <Icon name={expanded ? "shrink" : "expand"} />
            </button>
            <button type="button" onClick={() => setMode("closed")} title="Đóng" className="rounded-xl p-2 text-blue-100 transition hover:bg-white/15 hover:text-white">
              <Icon name="close" />
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto bg-[#f4f8fc] px-3 py-4 sm:px-4">
          <div className={`mx-auto space-y-4 ${expanded ? "max-w-5xl" : "max-w-full"}`}>
            {turns.map((turn) => (
              <article key={turn.key} className={turn.role === "user" ? "ml-auto max-w-[85%]" : "mr-auto max-w-full"}>
                <div
                  className={
                    turn.role === "user"
                      ? "ml-auto w-fit rounded-2xl rounded-br-md bg-[#005baa] px-4 py-2.5 text-sm leading-6 text-white shadow-sm"
                      : "w-fit whitespace-pre-line rounded-2xl rounded-bl-md border border-blue-50 bg-white px-4 py-3 text-sm leading-6 text-slate-700 shadow-sm"
                  }
                >
                  {turn.content}
                </div>
                {turn.degraded && (
                  <p className="mt-1.5 px-2 text-[11px] text-amber-700">
                    Vector chưa sẵn sàng, hệ thống đang dùng BM25 và bộ lọc dữ liệu.
                  </p>
                )}
                {turn.role === "assistant" && turn.generationProvider && (
                  <p className="mt-1.5 px-2 text-[10px] font-medium text-slate-400">
                    AI: {providerLabel(turn.generationProvider, turn.generationModel)}
                  </p>
                )}
                {turn.listings && turn.listings.length > 0 && (
                  <div className={`mt-3 grid gap-3 ${expanded ? "md:grid-cols-2 xl:grid-cols-3" : "grid-cols-1"}`}>
                    {turn.listings.map((listing) => {
                      const amenities = Object.entries(listing.amenities)
                        .filter(([key, value]) => value === true && amenityLabels[key])
                        .slice(0, 3);
                      return (
                        <div key={listing.id} className="group overflow-hidden rounded-2xl border border-blue-100 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
                          <div className="h-1 bg-gradient-to-r from-[#005baa] to-cyan-400" />
                          <div className="p-3.5">
                            <div className="flex items-start justify-between gap-2">
                              <span className="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[#005baa]">Gợi ý #{listing.rank}</span>
                              <span className="text-[11px] font-semibold text-slate-400">{Math.round(listing.similarity_score * 100)}% phù hợp</span>
                            </div>
                            <h3 className="mt-2 line-clamp-2 text-sm font-bold leading-5 text-slate-900">{listing.title}</h3>
                            <p className="mt-2 text-base font-black text-[#e34b4b]">{money(listing.price)}</p>
                            <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                              {listing.area ? `${listing.area} m² · ` : ""}{listing.address || listing.district || "Chưa rõ địa chỉ"}
                            </p>
                            {distance(listing.distance_to_ctu) && <p className="mt-1 text-xs font-medium text-[#005baa]">⌖ {distance(listing.distance_to_ctu)}</p>}
                            {listing.match_reasons.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {listing.match_reasons.map((reason) => <span key={reason} className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-medium text-emerald-700">✓ {reason}</span>)}
                              </div>
                            )}
                            {amenities.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {amenities.map(([key]) => <span key={key} className="rounded-md bg-slate-100 px-2 py-1 text-[10px] text-slate-600">{amenityLabels[key]}</span>)}
                              </div>
                            )}
                            <Link href={`/listings/${listing.id}`} className="mt-3 flex items-center justify-center rounded-xl bg-blue-50 px-3 py-2 text-xs font-bold text-[#005baa] transition group-hover:bg-[#005baa] group-hover:text-white">
                              Xem chi tiết phòng
                            </Link>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
                {turn.sources && turn.sources.length > 0 && (
                  <p className="mt-2 px-2 text-[10px] text-slate-400">
                    Dữ liệu: {turn.sources.map((source) => `#${source.rank} ${source.source}`).join(" · ")}
                  </p>
                )}
              </article>
            ))}

            {turns.length === 1 && (
              <div className="flex flex-wrap gap-2 pt-1">
                {QUICK_PROMPTS.map((prompt) => (
                  <button key={prompt} type="button" onClick={() => void send(prompt)} className="rounded-full border border-blue-200 bg-white px-3 py-2 text-left text-xs font-medium text-[#005baa] shadow-sm transition hover:border-[#005baa] hover:bg-blue-50">
                    {prompt}
                  </button>
                ))}
              </div>
            )}

            {loading && (
              <div className="flex w-fit items-center gap-1 rounded-2xl rounded-bl-md border border-blue-50 bg-white px-4 py-3 shadow-sm" aria-label="Đang tìm phòng">
                {[0, 1, 2].map((index) => <span key={index} className="h-2 w-2 animate-bounce rounded-full bg-[#005baa]" style={{ animationDelay: `${index * 120}ms` }} />)}
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <form onSubmit={submit} className="border-t border-blue-100 bg-white p-3">
          <div className={`mx-auto ${expanded ? "max-w-5xl" : "max-w-full"}`}>
            {error && <p className="mb-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</p>}
            <div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-1.5 focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-100">
              <textarea
                ref={inputRef}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                maxLength={2000}
                placeholder="Nhập nhu cầu tìm trọ..."
                className="max-h-24 min-h-[40px] min-w-0 flex-1 resize-none bg-transparent px-3 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400"
              />
              <button disabled={loading || message.trim().length < 2} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#005baa] text-white transition hover:bg-[#004a8f] disabled:cursor-not-allowed disabled:opacity-40" aria-label="Gửi câu hỏi">
                <Icon name="send" />
              </button>
            </div>
            <p className="mt-1.5 text-center text-[10px] text-slate-400">Nội dung chỉ tồn tại trong cửa sổ đang mở và không được lưu vào tài khoản.</p>
          </div>
        </form>
      </div>
    </section>
  );
}
