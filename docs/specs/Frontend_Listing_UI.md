# Spec — Frontend Listing UI

> Retrospective spec (viết sau khi code, theo format design-intent để pair với `docs/tech_specs/Frontend_Listing_UI.md`).

## Mục tiêu

Cho người dùng (guest + user) duyệt, lọc, sắp xếp, xem chi tiết và đăng/sửa tin phòng trọ
trên web, dựa trên 262 tin đã crawl + làm sạch ở backend. Đây là màn hình chính của app —
trước đó frontend chỉ có xác thực.

## Yêu cầu

Checklist theo FR-2 (SRS §Tìm kiếm & Xem tin):

- [x] FR-2.1 Tìm kiếm theo từ khóa (`q`) — trang `/`
- [x] FR-2.2 Lọc đa tiêu chí: giá min/max, diện tích min, quận (6 quận CT + "Tất cả").
      Chưa có filter theo tiện ích riêng, chưa có filter theo bán kính (xem FR-2.5).
- [x] FR-2.3 Sắp xếp: Mới nhất / Giá thấp→cao / Giá cao→thấp / Gần CTU nhất / Chất lượng
- [ ] FR-2.4 Bản đồ Leaflet/OSM tương tác, pin → popup — **chưa làm**, xem Ngoài phạm vi
- [ ] FR-2.5 Tìm theo bán kính trên bản đồ — **chưa làm** (phụ thuộc FR-2.4)
- [x] FR-2.6 Trang chi tiết: ảnh, giá, mô tả, địa chỉ, badge rủi ro, điểm chất lượng.
      Chưa có: gallery nhiều ảnh, bản đồ mini, badge nguồn/thời gian cập nhật.
- [ ] FR-2.7 So sánh 2-3 phòng — **chưa làm**, xem Ngoài phạm vi
- [ ] FR-2.8 Ẩn tin `status=expired` + badge "cập nhật X giờ trước" ở frontend — **chưa làm**
      (backend đã lọc `cleaning_status='cleaned'` nên tin bẩn/hết hạn không lộ ra, nhưng
      chưa có badge freshness hiển thị cho user)
- [x] (ngoài FR-2, bổ sung) Đăng tin `/listings/new` và sửa tin `/listings/[id]/edit` — cần
      đăng nhập, quyền sửa/xóa do backend enforce

## Ràng buộc

- **Đọc** (list/detail/map): Server Component gọi thẳng FastAPI qua `apiFetch` (server-side,
  `API_URL` nội bộ docker) — không lộ backend URL cho client, tốt cho SEO.
- **Ghi** (đăng/sửa/xóa): client form → Next Route Handler (`/api/listings`, `/api/listings/[id]`)
  → handler đọc token httpOnly qua `getAccessToken()` → gọi FastAPI kèm `Authorization: Bearer`.
  Token không bao giờ lộ ra client JS (nhất quán với `Frontend_Auth.md`).
- Next.js 14: không dùng `useSearchParams` ở page cần filter (gây lỗi build "Suspense
  boundary") → `ListingFilters` nhận giá trị ban đầu qua prop, tự đẩy query param lên URL.
- Build Docker standalone: tránh thêm dependency nặng (leaflet) khi chưa cần, do rủi ro
  build đã gặp trước đó.
- Quyền sửa/xóa thật do backend kiểm (`_check_owner` → 403); frontend chỉ ẩn/hiện nút gợi ý.

## Quyết định

- Kiến trúc Server Component (read) + Route Handler proxy (write), tái dùng pattern của
  luồng auth — không tạo pattern mới.
- Bản đồ: làm bản danh-sách-theo-khoảng-cách (`/map`, sort theo distance tới CTU) trước,
  Leaflet tương tác để iteration sau — đổi lấy giảm rủi ro build ngay bây giờ.
- Backend đã lọc sẵn tin sạch (`cleaning_status='cleaned' AND listing_type='phong_tro'` +
  tin user) → frontend không lọc lại, chỉ hiển thị.
- Badge rủi ro theo `risk_level`: safe=xanh lá, caution=hổ phách, suspicious=đỏ, unknown=xám.
- Backend đổi kèm: `ListingOut` thêm `description` + `quality_score`, thêm `SortBy.quality`
  (cần cho detail + sort chất lượng).

## Ngoài phạm vi

- Bản đồ Leaflet/OSM tương tác (pin + popup) và tìm theo bán kính (FR-2.4, FR-2.5).
- Upload ảnh trực tiếp cho form đăng tin (hiện chỉ nhận URL ảnh).
- So sánh 2-3 phòng (FR-2.7).
- Badge freshness "cập nhật X giờ trước" ở frontend (FR-2.8).
- Trang "Tin của tôi" (lọc theo `posted_by = current user`).
- Tích hợp gợi ý AI (sprint sau).

---
As-built: `docs/tech_specs/Frontend_Listing_UI.md`
