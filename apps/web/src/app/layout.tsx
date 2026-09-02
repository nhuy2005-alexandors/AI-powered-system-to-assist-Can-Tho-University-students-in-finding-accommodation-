import type { Metadata } from "next";
import ChatClient from "./chat/ChatClient";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trọ CTU — Tìm phòng trọ gần ĐH Cần Thơ",
  description: "Hệ thống tổng hợp & gợi ý nhà trọ AI cho sinh viên ĐH Cần Thơ",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="bg-paper font-sans text-ink antialiased">
        {children}
        <ChatClient />
      </body>
    </html>
  );
}
