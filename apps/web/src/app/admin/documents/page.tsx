import DocumentsClient from "./DocumentsClient";

export const dynamic = "force-dynamic";

export default function DocumentsPage() {
  return <div>
    <p className="text-sm font-bold uppercase tracking-widest text-emerald-600">Nguồn kiến thức</p>
    <h1 className="mt-1 text-3xl font-extrabold text-slate-950">Tài liệu chatbot</h1>
    <p className="mt-2 text-sm text-slate-500">Kiểm tra nội dung và chọn những tài liệu chatbot được phép sử dụng. Thay đổi được ghi nhận và áp dụng cho câu trả lời tiếp theo.</p>
    <DocumentsClient />
  </div>;
}
