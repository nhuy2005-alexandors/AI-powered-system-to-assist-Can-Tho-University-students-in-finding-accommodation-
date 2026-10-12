import Link from "next/link";
import { ktxDirectionsUrl, ktxMapUrl, type KtxCatalog } from "@/lib/ktx";

const services = [
  { icon: "⌁", title: "Kết nối và học tập", text: "Wi-Fi tại nơi ở hỗ trợ sinh viên học tập, tra cứu tài liệu và giữ liên lạc." },
  { icon: "▤", title: "Ăn uống, mua sắm", text: "Căn tin và siêu thị mini trong khuôn viên giúp việc ăn uống, mua sắm hằng ngày thuận tiện hơn." },
  { icon: "◷", title: "Tiện ích sinh hoạt", text: "Có khu vực gửi xe và giặt sấy phục vụ nhu cầu sinh hoạt thường ngày." },
  { icon: "◉", title: "An ninh khu nội trú", text: "Khu KTX có hàng rào, camera an ninh và lực lượng bảo vệ. Sinh viên cùng giữ gìn tài sản cá nhân và tuân thủ nội quy chung." },
];

const benefits = [
  { title: "Thuận tiện đến trường", text: "KTX nằm trong Khu II của Đại học Cần Thơ, thuận tiện cho việc học tập và sử dụng các tiện ích trong khuôn viên." },
  { title: "Thêm kết nối bạn bè", text: "Môi trường sống tập thể giúp sinh viên làm quen, chia sẻ kinh nghiệm và hỗ trợ nhau trong học tập, sinh hoạt." },
  { title: "Chủ động nếp sống", text: "Sinh viên rèn luyện tính tự lập, tinh thần trách nhiệm và thói quen tôn trọng không gian chung." },
];

export default function KtxScreen({ catalog }: { catalog: KtxCatalog }) {
  const semesterPrices = catalog.room_types
    .filter(room => room.price > 0 && room.price_period === "semester_3_5_months")
    .map(room => room.price);
  const minSemesterPrice = semesterPrices.length ? Math.min(...semesterPrices) : null;
  const maxSemesterPrice = semesterPrices.length ? Math.max(...semesterPrices) : null;

  return <main>
    <section className="relative isolate overflow-hidden bg-navy text-white">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/images/ktx/khu-b.jpg" alt="Khuôn viên ký túc xá Đại học Cần Thơ" className="absolute inset-0 -z-20 h-full w-full object-cover" />
      <div className="absolute inset-0 -z-10 bg-gradient-to-r from-[#042746]/95 via-[#042746]/85 to-[#042746]/30" />
      <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 sm:py-24">
        <p className="text-xs font-bold uppercase tracking-[.2em] text-sky-200">Đời sống sinh viên · CTU</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl">Ký túc xá Đại học Cần Thơ</h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-blue-100">Không gian nội trú dành cho sinh viên CTU, kết nối nơi ở, học tập và đời sống cộng đồng ngay tại Khu II.</p>
        <div className="mt-7 flex flex-wrap gap-3">
          <a href="#tien-ich" className="inline-flex min-h-12 items-center rounded-full bg-white px-6 text-sm font-bold text-navy hover:bg-blue-50">Khám phá tiện ích ↓</a>
          <a href="#dang-ky" className="inline-flex min-h-12 items-center rounded-full border border-white/50 px-6 text-sm font-semibold hover:bg-white/10">Tìm hiểu đăng ký</a>
          <Link href="/map?campus=1" className="inline-flex min-h-12 items-center rounded-full border border-white/50 px-6 text-sm font-semibold hover:bg-white/10">Xem vị trí trên bản đồ ↗</Link>
        </div>
        <div className="mt-10 flex flex-wrap gap-8 text-sm text-blue-100">
          <p><strong className="block text-2xl text-white">Khu A & Khu B</strong>tại Khu II, CTU</p>
          <p><strong className="block text-2xl text-white">Nội trú sinh viên</strong>học tập và sinh hoạt cộng đồng</p>
          {minSemesterPrice !== null && maxSemesterPrice !== null && <p><strong className="block text-2xl text-white">{minSemesterPrice.toLocaleString("vi-VN")}–{maxSemesterPrice.toLocaleString("vi-VN")} đ</strong>ước tính / người / học kỳ 3,5 tháng</p>}
        </div>
      </div>
      <span className="absolute bottom-3 right-5 text-xs text-white/80">Ảnh: Trung tâm Phục vụ sinh viên CTU</span>
    </section>

    <div className="mx-auto max-w-7xl space-y-14 px-5 py-10 sm:px-8">
      <section aria-labelledby="intro-title" className="grid gap-6 md:grid-cols-[1fr_1.2fr] md:items-center">
        <div><p className="text-xs font-bold uppercase tracking-widest text-primary">Tổng quan</p><h2 id="intro-title" className="mt-2 text-3xl font-bold">Một phần của đời sống CTU</h2></div>
        <div className="space-y-3 text-sm leading-7 text-ink-muted">
          <p>Ký túc xá Đại học Cần Thơ có khu A và khu B, cùng nằm tại {catalog.address}. Đây là lựa chọn lưu trú tập trung dành cho sinh viên muốn thuận tiện cho việc học và gắn bó với cộng đồng trong trường.</p>
          <p>Trang này giới thiệu tổng quan về môi trường nội trú, tiện ích, sinh hoạt và cách tìm hỗ trợ. Việc tiếp nhận sinh viên và sắp xếp chỗ ở do đơn vị quản lý KTX hướng dẫn theo thông báo từng năm học.</p>
        </div>
      </section>

      <section aria-labelledby="price-title" className="grid gap-6 rounded-3xl border border-line bg-white p-7 sm:p-9 md:grid-cols-[.8fr_1.2fr] md:items-center">
        <div><p className="text-xs font-bold uppercase tracking-widest text-primary">Chi phí tham khảo</p><h2 id="price-title" className="mt-2 text-3xl font-bold">Mức phí nội trú ước tính</h2></div>
        <div className="space-y-3">
          {minSemesterPrice !== null && maxSemesterPrice !== null
            ? <p className="text-2xl font-bold text-primary">{minSemesterPrice.toLocaleString("vi-VN")}–{maxSemesterPrice.toLocaleString("vi-VN")} đồng <span className="text-base font-medium text-ink-muted">/ người / học kỳ 3,5 tháng</span></p>
            : <p className="text-sm leading-6 text-ink-muted">Chưa có mức phí tham khảo để hiển thị.</p>}
          <p className="text-sm leading-6 text-ink-muted">Đây là khoảng giá tổng hợp từ danh mục tham khảo năm 2026, không phải báo giá cho một phòng cụ thể. Chưa bao gồm điện, nước; mức thu và chỗ còn trống cần xác nhận với văn phòng KTX trước khi đăng ký.</p>
        </div>
      </section>

      <section aria-labelledby="areas-title">
        <div className="mb-6"><p className="text-xs font-bold uppercase tracking-widest text-primary">Không gian nội trú</p><h2 id="areas-title" className="mt-2 text-3xl font-bold">Hai khu ký túc xá</h2><p className="mt-3 max-w-3xl text-sm leading-6 text-ink-muted">Khu A và khu B là hai khu nội trú trong Khu II. Thông tin vị trí trên bản đồ mang tính tham khảo; liên hệ văn phòng để được hướng dẫn đến đúng địa điểm.</p></div>
        <div className="grid gap-6 md:grid-cols-2">
          {catalog.dormitories.map(dorm => <article key={dorm.id} id={"khu-" + dorm.id.toLowerCase()} className="overflow-hidden rounded-3xl border border-line bg-white">
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={dorm.cover} alt={dorm.name + " — ảnh từ CTU"} className="h-56 w-full object-cover sm:h-64" loading="lazy" />
              <span className="absolute left-5 top-5 rounded-full bg-white px-4 py-2 text-sm font-bold text-navy">Khu {dorm.id}</span>
            </div>
            <div className="space-y-4 p-6"><h3 className="text-2xl font-bold">{dorm.name}</h3><p className="text-sm leading-6 text-ink-muted">Khu nội trú dành cho sinh viên Đại học Cần Thơ, đặt trong khuôn viên Khu II.</p>
              <div className="flex flex-wrap gap-3"><Link href={ktxMapUrl(dorm)} className="inline-flex min-h-11 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-white transition hover:bg-navy">Xem vị trí</Link><a href={ktxDirectionsUrl(dorm)} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center rounded-full border border-line px-5 text-sm font-semibold hover:bg-paper">Chỉ đường ↗</a></div>
            </div>
          </article>)}
        </div>
      </section>

      <section id="tien-ich" className="scroll-mt-6" aria-labelledby="services-title">
        <p className="text-xs font-bold uppercase tracking-widest text-primary">Dịch vụ & tiện ích</p><h2 id="services-title" className="mt-2 text-3xl font-bold">Hỗ trợ nhu cầu sinh hoạt hằng ngày</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{services.map(service => <article key={service.title} className="rounded-2xl border border-line bg-white p-5"><span aria-hidden="true" className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-soft text-xl font-bold text-primary">{service.icon}</span><h3 className="mt-4 font-bold">{service.title}</h3><p className="mt-2 text-sm leading-6 text-ink-muted">{service.text}</p></article>)}</div>
        <p className="mt-4 text-xs leading-5 text-ink-muted">Thông tin tiện ích tổng hợp từ các trang giới thiệu và hướng dẫn của CTU; cách cung cấp có thể thay đổi theo thông báo của KTX.</p>
      </section>

      <section aria-labelledby="benefits-title">
        <div className="grid gap-6 md:grid-cols-[.8fr_1.2fr]"><div><p className="text-xs font-bold uppercase tracking-widest text-primary">Lợi ích</p><h2 id="benefits-title" className="mt-2 text-3xl font-bold">Ở gần trường, thêm kết nối</h2><p className="mt-3 text-sm leading-6 text-ink-muted">Môi trường nội trú giúp sinh viên có thêm điều kiện thuận lợi để học tập và tự lập trong thời gian ở trường.</p></div>
          <div className="grid gap-3">{benefits.map((benefit, index) => <article key={benefit.title} className="flex gap-4 rounded-2xl border border-line bg-white p-5"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-bold text-primary">0{index + 1}</span><div><h3 className="font-bold">{benefit.title}</h3><p className="mt-1 text-sm leading-6 text-ink-muted">{benefit.text}</p></div></article>)}</div>
        </div>
      </section>

      <section aria-labelledby="activities-title" className="rounded-3xl bg-[#eaf3fb] p-7 sm:p-10">
        <p className="text-xs font-bold uppercase tracking-widest text-primary">Sinh hoạt & kết nối</p><h2 id="activities-title" className="mt-2 text-3xl font-bold">Cùng xây dựng nếp sống tập thể</h2>
        <div className="mt-4 grid gap-6 md:grid-cols-2"><div><p className="text-sm leading-7 text-ink-muted">Sinh viên có thể học nhóm, giao lưu với bạn cùng khu, chia sẻ kinh nghiệm và tham gia các hoạt động chung do trường hoặc đơn vị quản lý thông báo. Lịch hoạt động thay đổi theo từng thời điểm, nên hãy theo dõi kênh chính thức của CTU và KTX để cập nhật.</p>
          <ul className="mt-4 grid gap-3 text-sm text-ink-muted sm:grid-cols-3"><li className="rounded-xl bg-white p-4"><strong className="block text-ink">Học tập</strong><span className="mt-1 block">Học nhóm, hỗ trợ nhau trong học tập</span></li><li className="rounded-xl bg-white p-4"><strong className="block text-ink">Giao lưu</strong><span className="mt-1 block">Kết nối bạn bè, chia sẻ đời sống sinh viên</span></li><li className="rounded-xl bg-white p-4"><strong className="block text-ink">Sinh hoạt chung</strong><span className="mt-1 block">Tham gia hoạt động theo thông báo của trường</span></li></ul></div>
          <div className="rounded-2xl bg-white p-5"><h3 className="font-bold">Tôn trọng không gian chung</h3><p className="mt-2 text-sm leading-6 text-ink-muted">Giữ gìn vệ sinh, trật tự và thực hiện nội quy là cách mỗi sinh viên góp phần tạo nên môi trường sống an toàn, thân thiện.</p><a href="https://ssc.ctu.edu.vn/images/upload/Noiquy_KTX_trich_092025.pdf" target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs font-semibold text-primary underline">Xem nội quy KTX CTU ↗</a></div>
        </div>
      </section>

      <section id="dang-ky" className="scroll-mt-6" aria-labelledby="support-title">
        <div className="rounded-3xl bg-navy p-7 text-white sm:p-10">
          <p className="text-xs font-bold uppercase tracking-widest text-sky-200">Đăng ký & hỗ trợ</p><h2 id="support-title" className="mt-2 text-3xl font-bold">KTX đồng hành từ bước tìm hiểu</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-blue-100">Sinh viên có thể xem hướng dẫn và đăng ký qua hệ thống của CTU. Tân sinh viên chưa có tài khoản hãy tham khảo hướng dẫn riêng. Nếu cần hỏi về hồ sơ, thời gian tiếp nhận, chỗ ở hoặc các thủ tục trong quá trình lưu trú, vui lòng liên hệ trực tiếp văn phòng KTX để được hướng dẫn theo tình hình hiện tại.</p>
          <div className="mt-6 flex flex-wrap gap-3"><a href={catalog.registration_url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center rounded-full bg-white px-5 text-sm font-bold text-navy">Hướng dẫn đăng ký CTU ↗</a></div>
          <div className="mt-7 grid gap-4 border-t border-white/20 pt-6 sm:grid-cols-3"><div><p className="text-xs text-blue-200">Email KTX</p><a href={"mailto:" + catalog.email} className="mt-1 inline-block font-semibold underline">{catalog.email}</a></div>{catalog.dormitories.map(dorm => <div key={dorm.id}><p className="text-xs text-blue-200">Văn phòng khu {dorm.id}</p><a href={"tel:" + dorm.phone.replace(/\D/g, "")} className="mt-1 inline-block font-semibold underline">{dorm.phone}</a></div>)}</div>
          <p className="mt-4 text-xs leading-5 text-blue-200">Số điện thoại theo thông báo KTX năm học 2026–2027. Vui lòng gọi xác nhận trước khi đến.</p>
        </div>
      </section>

      <footer className="border-t border-line pt-6 text-xs leading-6 text-ink-muted"><p>Nội dung giới thiệu được tổng hợp từ nguồn công khai của Đại học Cần Thơ. Thông tin tuyển ở, thời gian, tiện ích và thủ tục có thể cập nhật theo từng năm học.</p><details className="mt-2"><summary className="cursor-pointer font-semibold text-ink">Nguồn thông tin</summary><ul className="mt-3 space-y-2">{catalog.sources.filter(item => item.url).map(item => <li key={item.id}><a href={item.url!} target="_blank" rel="noreferrer" className="text-primary underline">{item.title} ↗</a> — {item.note}</li>)}</ul></details></footer>
    </div>
  </main>;
}
