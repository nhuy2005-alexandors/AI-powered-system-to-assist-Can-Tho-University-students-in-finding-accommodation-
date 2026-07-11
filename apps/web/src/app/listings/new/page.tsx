import ListingForm from "../ListingForm";

export default function NewListingPage() {
  return (
    <main className="min-h-screen bg-slate-50 p-4 sm:p-8">
      <div className="mx-auto max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-800">Đăng tin cho thuê</h1>
        <div className="mt-6">
          <ListingForm mode="create" />
        </div>
      </div>
    </main>
  );
}
