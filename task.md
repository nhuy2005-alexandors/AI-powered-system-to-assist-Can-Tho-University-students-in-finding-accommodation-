# Agent Task & Checkpoint Board (Stigmergy)

Đây là nơi các AI Agent (Omni-Assistant, Claude Code, Sub-agents) giao tiếp, ghi chú lại các công việc đang làm, đã làm xong và bàn giao bối cảnh cho nhau.

## 📌 Trạng thái Hiện tại (Current Checkpoint)
- **Ngày cập nhật:** 2026-07-03
- **Context:** Hệ thống Crawler Pipeline đã được tích hợp thêm 2 nguồn địa phương Cần Thơ (nhadatcantho, nhadatcantho247). Data Cleaning Pipeline đã được thiết lập để tự động chạy sau khi crawler lấy dữ liệu về.
- **[Claude Code — 2026-07-03]** Hoàn tất Sprint 1.10 (UGC Listing CRUD), thêm nguồn crawler `bds123`, và toàn bộ luồng **Xác thực Frontend** (đăng ký / đăng nhập / hồ sơ) với token lưu trong httpOnly cookie. Tất cả verified end-to-end với DB & stack docker thật.
- **[Claude Code — 2026-07-03] Làm mượt Crawler Pipeline — 6/6 nguồn giờ có dữ liệu sạch trong DB.** Sửa 3 nguồn chết (bds123/mogi/nhadatcantho — sai URL & crash), làm cleaner chạy cho cả trigger tay, backfill district + toạ độ. Verified: 337 tin (324 cleaned / 14 rejected), 0 tin kẹt 'raw', 59 test pass. Xem `docs/tech_specs/Crawler_Pipeline_Hardening.md`.
- **[Claude Code — 2026-07-03] Pipeline làm sạch đa tầng (5 tầng) — data phân loại + chấm điểm cho backend & AI.** classify (phong_tro/nha/mặt bằng/khác) → validate giá theo loại → resolve area → normalize → quality_score 0..1. Migration 70 (listing_type + quality_score). Search mặc định chỉ trả phòng trọ sạch (ẩn nhà/mặt bằng). Verified: 86 test pass, 299 cleaned/14 rejected, avg quality 0.84, search=262 tin phong_tro. Xem `docs/tech_specs/Data_Cleaning_Pipeline_Design.md` + `Crawler_Data_Quality_Assessment.md`.
- **[Claude Code — 2026-07-03] Sprint 2 Frontend Listing UI — màn hình chính đã sống.** Trang danh sách+lọc (/), chi tiết (/listings/[id]), bản đồ/nearby (/map), form đăng/sửa tin (/listings/new, /edit) qua Route Handler proxy (token httpOnly). Sửa bds123 address selector (banner bug) + bật CRAWLER_ENABLED (scheduler tự cào 12 job). Verified: build pass, mọi trang 200, create flow end-to-end OK. Xem `docs/tech_specs/Frontend_Listing_UI.md`.

## 🚀 Nhiệm vụ Đã Hoàn Thành (Completed Tasks)
- [x] Tạo Data Cleaning Pipeline (`cleaner/pipeline.py`) để nội suy diện tích, loại bỏ tin rác, chuẩn hóa tiêu đề.
- [x] Tích hợp Cleaning Pipeline vào tiến trình chạy nền của `scheduler.py`.
- [x] Thu thập CSS Selectors và cấu hình 2 nguồn dữ liệu địa phương Cần Thơ bằng JSON Config.
- [x] Kích hoạt 2 crawler địa phương trong `ENABLED_SOURCES`.
- [x] Hoàn thiện tài liệu luồng dữ liệu Crawler ra Mermaid diagram (lưu ở `docs/tech_specs/Crawler_Pipeline.md`).
- [x] **[CC] UGC Listing CRUD** — `POST/PUT/DELETE /listings` (đăng/sửa/ẩn tin của user). Kiểm tra chủ sở hữu, soft-delete (`status='hidden'`), 7 test e2e DB thật. Migration `50_ugc.sql`. Xem `docs/tech_specs/UGC_Listing_CRUD.md`.
- [x] **[CC] Nguồn crawler `bds123`** — JSON config CSS-selector, kích hoạt trong `ENABLED_SOURCES`. Parse 9 card OK trên HTML thật.
- [x] **[CC] Xác thực Frontend (Auth)** — trang login/register/me (Next.js App Router), token access+refresh lưu httpOnly cookie qua Route Handler proxy → FastAPI. Middleware bảo vệ route. Xem `docs/tech_specs/Frontend_Auth.md`.

## 🚀 Nhiệm vụ Đã Hoàn Thành (Completed Tasks) — tiếp
- [x] **[CC] Làm mượt Crawler Pipeline (2026-07-03)** — 6/6 nguồn có data sạch. Chi tiết `docs/tech_specs/Crawler_Pipeline_Hardening.md`.
- [x] **[CC] Pipeline làm sạch đa tầng + phân loại + quality_score (2026-07-03)** — chi tiết `docs/tech_specs/Data_Cleaning_Pipeline_Design.md`. Search giờ chỉ trả phòng trọ sạch.

## 🚀 Nhiệm vụ Đã Hoàn Thành (Completed Tasks) — tiếp
- [x] **[CC] Frontend Listing UI + đăng/sửa tin (2026-07-03)** — list/detail/map/form. Chi tiết `docs/tech_specs/Frontend_Listing_UI.md`.
- [x] **[CC] Sửa bds123 address selector + bật scheduler tự cào** — address giờ sạch, CRAWLER_ENABLED=true (12 job).

## ⏳ Nhiệm vụ Đang Chờ / Tiếp theo (Pending / Next Tasks)
- [ ] Tích hợp tính năng AI Recommendation & Chatbot RAG với pgvector (đã có `quality_score` + `listing_type` để lọc tập học sạch).
- [ ] Bản đồ tương tác (leaflet) thay bản danh-sách-khoảng-cách hiện tại; upload ảnh cho form đăng tin; trang "Tin của tôi".
- [ ] **Cải thiện classifier:** mogi/nhadatcantho247 nhiều tin lọt `khac` (title không keyword rõ) → bị ẩn khỏi search. Mở rộng keyword hoặc phân loại từ URL chuyên mục.
- [ ] ~14 tin nhadatcantho247 thiếu district (address nguồn quá ngắn).
- [ ] (Tùy chọn) Tích hợp giải pháp Proxy / Anti-bot cho crawler vào `fetcher.py`.

## 📚 Đặc Tả Kỹ Thuật (Technical Specs)
- **Thư mục lưu trữ tài liệu kỹ thuật:** `docs/tech_specs/`
- Mọi sơ đồ hệ thống, quy trình luồng dữ liệu (Mermaid) cần được các agent lưu vào thư mục trên để giữ cho codebase gọn gàng.
