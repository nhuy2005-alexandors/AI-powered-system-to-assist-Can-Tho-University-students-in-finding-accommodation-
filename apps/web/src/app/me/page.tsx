import { redirect } from "next/navigation";
import Link from "next/link";
import { getCurrentUser } from "@/lib/current-user";
import LogoutButton from "./LogoutButton";
import SiteHeader from "../SiteHeader";

export default async function MePage() {
  const user = await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen bg-paper">
      <SiteHeader />
      <main className="mx-auto max-w-[1160px] px-5 py-10 sm:px-10">
        <div className="mb-7">
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-primary">Tài khoản</p>
          <h1 className="mt-1 text-3xl font-extrabold text-ink">Xin chào, {user.name || "bạn"}</h1>
          <p className="mt-2 text-ink-muted">Quản lý bài đăng và tiếp tục tìm phòng phù hợp với bạn.</p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
          <section className="rounded-2xl border border-line bg-white p-6 shadow-sm">
            <div className="flex items-center gap-4">
              {user.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={user.avatar_url} alt={user.name ?? user.email} className="h-16 w-16 rounded-full object-cover" />
              ) : (
                <span className="grid h-16 w-16 place-items-center rounded-full bg-emerald-100 text-2xl font-black text-emerald-700">{(user.name || user.email).charAt(0).toUpperCase()}</span>
              )}
              <div className="min-w-0">
                <p className="truncate text-lg font-bold text-ink">{user.name || "Chưa cập nhật tên"}</p>
                <p className="truncate text-sm text-ink-muted">{user.email}</p>
                <span className="mt-2 inline-block rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-700">{user.role}</span>
              </div>
            </div>
            <div className="mt-6 border-t border-line pt-5">
              <LogoutButton />
            </div>
          </section>

          <section className="grid gap-4 sm:grid-cols-2">
            <Link href="/" className="group rounded-2xl border border-line bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-blue-50 text-xl text-primary">⌕</span>
              <h2 className="mt-4 text-lg font-extrabold text-ink">Về trang tìm trọ</h2>
              <p className="mt-2 text-sm leading-6 text-ink-muted">Xem danh sách phòng, bộ lọc và gợi ý gần Đại học Cần Thơ.</p>
            </Link>
            <Link href="/listings/mine" className="group rounded-2xl border border-line bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-50 text-xl text-emerald-700">▤</span>
              <h2 className="mt-4 text-lg font-extrabold text-ink">Tin của tôi</h2>
              <p className="mt-2 text-sm leading-6 text-ink-muted">Xem, sửa hoặc quản lý những phòng trọ bạn đã đăng.</p>
            </Link>
            <Link href="/listings/new" className="group rounded-2xl border border-line bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-amber-50 text-xl text-amber-700">＋</span>
              <h2 className="mt-4 text-lg font-extrabold text-ink">Đăng tin mới</h2>
              <p className="mt-2 text-sm leading-6 text-ink-muted">Đăng phòng trọ miễn phí và để Risk kiểm tra thông tin.</p>
            </Link>
            {user.role === "admin" ? (
              <Link href="/admin" className="group rounded-2xl bg-[#0b1f33] p-6 text-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-white/10 text-xl text-emerald-300">▦</span>
                <h2 className="mt-4 text-lg font-extrabold">Mở trang quản trị</h2>
                <p className="mt-2 text-sm leading-6 text-slate-300">Dashboard, kiểm duyệt báo cáo, bài tin và người dùng.</p>
              </Link>
            ) : (
              <Link href="/chat" className="group rounded-2xl border border-line bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-violet-50 text-xl text-violet-700">✦</span>
                <h2 className="mt-4 text-lg font-extrabold text-ink">Trợ lý AI</h2>
                <p className="mt-2 text-sm leading-6 text-ink-muted">Mô tả nhu cầu để AI tìm và giải thích các phòng phù hợp.</p>
              </Link>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
