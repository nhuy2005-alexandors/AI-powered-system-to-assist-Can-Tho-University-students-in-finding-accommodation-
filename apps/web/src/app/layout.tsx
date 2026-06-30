import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trọ CTU",
  description: "Hệ thống tổng hợp & gợi ý nhà trọ AI cho sinh viên ĐH Cần Thơ",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
