# Đặc tả kỹ thuật — Frontend Listing UI (Sprint 2)

> Ngày: 2026-07-03 · Trạng thái: **Hoàn tất, verified end-to-end với backend + data thật**

## 1. Mục tiêu

Cho người dùng **duyệt, lọc, xem chi tiết, đăng/sửa** tin phòng trọ trên web. Đây là màn
hình chính của ứng dụng — trước đó frontend mới chỉ có xác thực. Backend đã sẵn 262 tin
phòng trọ sạch (có toạ độ, điểm chất lượng).

## 2. Các trang đã xây

| Trang | Đường dẫn | Loại | Chức năng |
|-------|-----------|------|-----------|
| Danh sách | `/` (trang chủ) | Server | Lưới tin + thanh lọc + phân trang |
| Chi tiết | `/listings/[id]` | Server | Ảnh, giá, mô tả, địa chỉ, badge rủi ro, điểm chất lượng |
| Bản đồ | `/map` | Server | Tin gần CTU sắp theo khoảng cách (bản đồ tương tác để sau) |
| Đăng tin | `/listings/new` | Server + form | Form tạo tin (cần đăng nhập) |
| Sửa tin | `/listings/[id]/edit` | Server + form | Form sửa (chủ tin/admin) |

## 3. Kiến trúc: Server Component + Route Handler proxy

Nhất quán với luồng auth (xem `Frontend_Auth.md`):
- **Đọc dữ liệu** (list/detail/map): Server Component gọi thẳng FastAPI qua `apiFetch`
  (server-side, dùng `API_URL` nội bộ docker) — SEO tốt, không lộ API cho client.
- **Ghi dữ liệu** (đăng/sửa/xóa): form ở client → POST tới **Next Route Handler**
  (`/api/listings`, `/api/listings/[id]`) → handler đọc token httpOnly qua `getAccessToken()`
  → gọi FastAPI kèm `Authorization: Bearer`. Token **không bao giờ** lộ ra client JS.

```
Đọc:  [Server Component] --apiFetch--> [FastAPI GET /listings]
Ghi:  [Client form] --POST--> [Next Route Handler] --Bearer token--> [FastAPI POST/PUT/DELETE]
```

## 4. Thành phần chính

| File | Vai trò |
|------|---------|
| `lib/api.ts` | Thêm: types `ListingOut/SearchResult/ListingInput` + hàm `searchListings/getListing/getNearby/createListing/updateListing/deleteListing` |
| `lib/format.ts` | Helper: `formatPrice` (VND→"X.X triệu/tháng"), `formatArea`, `formatDistance` (m→km), `riskBadge` (màu theo mức rủi ro) |
| `app/page.tsx` | Trang danh sách (thay trang health-check cũ) |
| `app/ListingFilters.tsx` | Thanh lọc (client) — đẩy query param lên URL |
| `app/ListingCard.tsx` | Thẻ tin |
| `app/listings/[id]/page.tsx` | Chi tiết + nút Sửa/Xóa nếu là tin user |
| `app/listings/ListingForm.tsx` | Form dùng chung đăng/sửa (react-hook-form + zod) |
| `app/api/listings/route.ts` + `[id]/route.ts` | Route Handler POST/PUT/DELETE |
| `middleware.ts` | Thêm `/listings/new` + regex `/listings/[id]/edit` vào route bảo vệ |

## 5. Bộ lọc & sắp xếp (consume `GET /listings`)

- Tìm text (q), quận (dropdown 6 quận CT + "Tất cả"), giá min/max, diện tích min.
- Sắp xếp: Mới nhất / Giá thấp→cao / Giá cao→thấp / Gần CTU nhất / **Chất lượng**.
- Cơ chế: thanh lọc đẩy query param lên URL → Server Component fetch lại. `ListingFilters`
  nhận giá trị ban đầu qua **prop** (không dùng `useSearchParams`) → tránh lỗi build
  "Suspense boundary" của Next 14.

## 6. Quyết định thiết kế đáng chú ý

- **Backend đã lọc sẵn** tin phòng trọ sạch (`cleaning_status='cleaned' AND listing_type='phong_tro'`
  + tin user) → frontend không cần lọc lại, chỉ hiển thị.
- **Nút Sửa/Xóa** hiện khi `source==='user'` + đã đăng nhập. Quyền THẬT do backend kiểm
  (`_check_owner` → 403). Frontend chỉ gợi ý UI, không phải cổng bảo mật.
- **Bản đồ** làm bản danh-sách-theo-khoảng-cách trước (tránh rủi ro build khi thêm
  leaflet vào Docker standalone). Bản đồ tương tác để iteration sau.
- **Badge rủi ro**: safe=xanh lá, caution=hổ phách, suspicious=đỏ, unknown=xám (từ `risk_level`).

## 7. Thay đổi backend đi kèm

`ListingOut` bổ sung `description` + `quality_score` (trước thiếu — detail cần mô tả, sort cần điểm).
Thêm `SortBy.quality`. Áp dụng vào `_COLS` query + schema.

## 8. Kiểm chứng (verified, không mock)

- `docker compose build web`: **build pass** (13 route compile, không lỗi type/Suspense).
- Mọi trang trả **200**: home (thấy "triệu/tháng" 40x, các quận), chi tiết, map (100 tin "cách CTU"),
  filter theo quận+sort.
- Chi tiết id không tồn tại → **404** đúng.
- `/listings/new` chưa đăng nhập → **307 redirect** `/login?next=/listings/new`.
- Luồng tạo tin có xác thực: đăng ký → tạo tin (201, `source='user'`) → xem chi tiết được
  → xuất hiện trong tìm kiếm. Tin user luôn hiển thị dù chưa qua cleaner.

## 9. Việc tiếp theo

- Bản đồ tương tác (leaflet) thay bản danh sách khoảng cách.
- Upload ảnh cho form đăng tin (hiện chỉ nhận URL ảnh).
- Trang "Tin của tôi" (lọc `posted_by = current user`).
- Tích hợp AI gợi ý (Sprint sau) — đã có `quality_score` + `listing_type` để lọc tập tốt.
