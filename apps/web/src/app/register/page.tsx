import Link from "next/link";
import RegisterForm from "./RegisterForm";

export default function RegisterPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-800">Đăng ký</h1>

        <div className="mt-6">
          <RegisterForm />
        </div>

        <p className="mt-6 text-center text-sm text-slate-600">
          Đã có tài khoản?{" "}
          <Link href="/login" className="font-medium text-emerald-600 hover:text-emerald-700">
            Đăng nhập
          </Link>
        </p>
      </div>
    </main>
  );
}
