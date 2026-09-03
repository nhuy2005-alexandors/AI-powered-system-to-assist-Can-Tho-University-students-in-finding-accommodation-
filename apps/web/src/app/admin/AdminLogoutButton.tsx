"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function AdminLogoutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  async function logout() {
    setLoading(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.push("/");
      router.refresh();
    }
  }
  return (
    <button type="button" onClick={logout} disabled={loading} className="rounded-lg bg-red-500/15 px-3 py-2 text-xs font-semibold text-red-200 hover:bg-red-500/25 disabled:opacity-50">
      {loading ? "Đang thoát" : "Đăng xuất"}
    </button>
  );
}
