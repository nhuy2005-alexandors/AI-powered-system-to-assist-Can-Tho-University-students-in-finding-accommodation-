import type { Metadata } from "next";
import Link from "next/link";
import { getKtxCatalog } from "@/lib/api";
import SiteHeader from "../SiteHeader";
import KtxScreen from "./KtxScreen";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Ký túc xá Đại học Cần Thơ | Trọ CTU",
  description: "Giới thiệu tổng quan KTX Đại học Cần Thơ: môi trường nội trú, tiện ích, sinh hoạt sinh viên, đăng ký và hỗ trợ.",
};

export default async function KtxPage() {
  let catalog;
  try { catalog = await getKtxCatalog(); } catch { /* Show an actionable empty state. */ }
  return <div className="min-h-screen bg-paper text-ink">
    <SiteHeader />
    {catalog ? <KtxScreen catalog={catalog} /> : <main className="mx-auto max-w-3xl px-5 py-20">
      <h1 className="text-3xl font-bold">Ký túc xá Đại học Cần Thơ</h1>
      <p className="mt-4 text-ink-muted">Danh mục KTX đang được cập nhật. Vui lòng tải lại trang sau hoặc liên hệ văn phòng KTX.</p>
      <a href="https://ssc.ctu.edu.vn/hoat/213-ktx25.html" target="_blank" rel="noreferrer" className="mt-6 inline-block text-primary underline">Thông tin từ CTU ↗</a>
      <Link href="/map" className="ml-6 text-primary underline">Mở bản đồ</Link>
    </main>}
  </div>;
}

