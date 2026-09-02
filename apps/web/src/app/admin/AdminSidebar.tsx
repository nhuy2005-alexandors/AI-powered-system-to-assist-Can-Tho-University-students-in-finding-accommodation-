"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { User } from "@/lib/api";
import AdminLogoutButton from "./AdminLogoutButton";

const NAV = [
  { href: "/admin", label: "Dashboard", icon: "▦" },
  { href: "/admin/reports", label: "Báo cáo tin", icon: "⚑" },
  { href: "/admin/listings", label: "Quản lý bài tin", icon: "▤" },
  { href: "/admin/users", label: "Người dùng", icon: "♙" },
];

function active(pathname: string, href: string) {
  return href === "/admin" ? pathname === href : pathname.startsWith(href);
}

export default function AdminSidebar({ user }: { user: User }) {
  const pathname = usePathname();
  return (
    <aside className="border-b border-slate-800 bg-[#0b1f33] text-white lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:flex lg:w-72 lg:flex-col lg:border-b-0 lg:border-r">
      <div className="flex h-20 items-center gap-3 border-b border-white/10 px-6">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-500 text-xl font-black text-white">T</div>
        <div>
          <p className="text-lg font-extrabold">Trọ CTU Admin</p>
          <p className="text-xs text-slate-400">Trung tâm quản trị hệ thống</p>
        </div>
      </div>

      <nav className="flex gap-2 overflow-x-auto px-4 py-4 lg:flex-1 lg:flex-col lg:overflow-visible lg:py-6">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex shrink-0 items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition ${
              active(pathname, item.href)
                ? "bg-emerald-500 text-white shadow-lg shadow-emerald-950/20"
                : "text-slate-300 hover:bg-white/10 hover:text-white"
            }`}
          >
            <span className="grid h-6 w-6 place-items-center text-lg" aria-hidden="true">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="hidden border-t border-white/10 p-4 lg:block">
        <Link href="/me" className="flex items-center gap-3 rounded-xl p-3 hover:bg-white/10">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-slate-700 font-bold text-emerald-300">
            {(user.name || user.email).charAt(0).toUpperCase()}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold">{user.name || "Quản trị viên"}</span>
            <span className="block truncate text-xs text-slate-400">{user.email}</span>
          </span>
        </Link>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <Link href="/" className="rounded-lg bg-white/10 px-3 py-2 text-center text-xs font-semibold text-slate-200 hover:bg-white/20">
            Trang chính
          </Link>
          <AdminLogoutButton />
        </div>
      </div>
    </aside>
  );
}
