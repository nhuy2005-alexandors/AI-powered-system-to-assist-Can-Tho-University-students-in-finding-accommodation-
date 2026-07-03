import Link from "next/link";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-800">Đăng nhập</h1>

        <div className="mt-6">
          <LoginForm />
        </div>

        <p className="mt-6 text-center text-sm text-slate-600">
          Chưa có tài khoản?{" "}
          <Link href="/register" className="font-medium text-emerald-600 hover:text-emerald-700">
            Đăng ký
          </Link>
        </p>
      </div>
    </main>
  );
}
