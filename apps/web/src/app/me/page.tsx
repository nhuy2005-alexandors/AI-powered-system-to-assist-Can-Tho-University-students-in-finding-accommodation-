import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/current-user";
import LogoutButton from "./LogoutButton";

export default async function MePage() {
  const user = await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-800">Tài khoản của tôi</h1>

        <div className="mt-6 flex items-center gap-4">
          {user.avatar_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={user.avatar_url}
              alt={user.name ?? user.email}
              className="h-16 w-16 rounded-full object-cover"
            />
          )}
          <div>
            <p className="text-lg font-medium text-slate-800">
              {user.name || "—"}
            </p>
            <p className="text-sm text-slate-600">{user.email}</p>
            <span className="mt-1 inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
              {user.role}
            </span>
          </div>
        </div>

        <div className="mt-6">
          <LogoutButton />
        </div>
      </div>
    </main>
  );
}
