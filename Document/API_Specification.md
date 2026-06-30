# Đặc Tả API (API Specification)
## Hệ thống tổng hợp & gợi ý nhà trọ AI — THS2026-66

**Phiên bản:** 1.0 · **Base URL:** `http://localhost:8000` (dev) · **Format:** JSON

## Quy ước chung
- Auth: `Authorization: Bearer <access_token>` (JWT). Route công khai đánh dấu 🌐.
- Mã lỗi: `400` validate, `401` chưa auth, `403` thiếu quyền, `404` không thấy, `429` rate-limit, `500` lỗi server.
- Phân trang: query `?page=1&size=20`, response kèm `{ "total", "page", "size", "items" }`.
- Thời gian: ISO 8601 UTC.

---

## 1. Auth (`/auth`)

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| POST | `/auth/register` | Đăng ký, gửi OTP email | 🌐 |
| POST | `/auth/verify-otp` | Xác thực OTP kích hoạt tài khoản | 🌐 |
| POST | `/auth/login` | Đăng nhập → access + refresh token | 🌐 |
| POST | `/auth/google` | OAuth 2.0 Google | 🌐 |
| POST | `/auth/refresh` | Làm mới access token | 🌐 |
| POST | `/auth/forgot-password` | Gửi link reset | 🌐 |
| POST | `/auth/reset-password` | Đặt mật khẩu mới | 🌐 |
| GET | `/auth/me` | Thông tin user hiện tại | ✓ |

**POST /auth/login**
```jsonc
// request
{ "email": "sv@student.ctu.edu.vn", "password": "***" }
// 200
{ "access_token": "ey...", "refresh_token": "ey...", "token_type": "bearer",
  "user": { "id": 1, "name": "Trần Phú", "role": "user" } }
// 401
{ "detail": "Invalid email or password" }
```

---

## 2. Listings (`/listings`)

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| GET | `/listings` | Tìm kiếm + lọc + sắp xếp + phân trang | 🌐 |
| GET | `/listings/{id}` | Chi tiết 1 tin | 🌐 |
| GET | `/listings/nearby` | Tìm theo bán kính (lat,lng,radius) | 🌐 |
| POST | `/listings` | Đăng tin UGC (qua AI Risk Check) | ✓ |
| PUT | `/listings/{id}` | Sửa tin của mình | ✓ |
| DELETE | `/listings/{id}` | Ẩn tin của mình (soft) | ✓ |
| POST | `/listings/{id}/report` | Báo cáo tin sai | ✓ |

**GET /listings** — query params:
`q`, `min_price`, `max_price`, `min_area`, `district`, `amenities` (csv), `max_distance_ctu`, `sort` (`price_asc`|`price_desc`|`newest`|`nearest`|`freshness`), `page`, `size`.
```jsonc
// 200 — chỉ trả status=active, kèm freshness
{ "total": 142, "page": 1, "size": 20, "items": [
  { "id": 1, "title": "Phòng gần CTU", "price": 2500000, "area": 25,
    "district": "Ninh Kiều", "lat": 10.03, "lng": 105.77,
    "distance_to_ctu": 800, "risk_score": 0.1, "risk_level": "safe",
    "freshness_score": 0.95, "last_seen": "2026-06-29T02:00:00Z",
    "source": "phongtro123", "images": ["..."] } ] }
```

---

## 3. Recommendation (`/recommend`)

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| POST | `/recommend/quiz` | Nộp onboarding quiz → tạo preference_vector | ✓ |
| GET | `/recommend/for-you` | Top-10 gợi ý (cold-start fallback popularity) | ✓ |
| GET | `/recommend/popular` | Top-10 phổ biến (guest dùng được) | 🌐 |
| POST | `/recommend/feedback` | Ghi implicit feedback (view/bookmark/click) | ✓ |

```jsonc
// POST /recommend/feedback
{ "listing_id": 1, "type": "bookmark", "duration_ms": 4200 }
```

---

## 4. Roommate Matching (`/matching`)

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| POST | `/matching/profile` | Lưu hồ sơ 6 câu → matching_vector | ✓ |
| GET | `/matching/candidates` | DS tương thích (Weighted Cosine ≥0.7) | ✓ |
| POST | `/matching/invite` | Gửi lời mời kết nối | ✓ |
| POST | `/matching/invite/{id}/respond` | Chấp nhận/từ chối; accept → lộ liên hệ | ✓ |

```jsonc
// GET /matching/candidates → 200
{ "items": [ { "user_id": 8, "name": "Phúc", "score": 0.85,
  "habits": { "sleep_time": 1, "smoke": false, "cleanliness": 4 } } ] }
```

---

## 5. Chatbot RAG (`/chat`)

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| POST | `/chat/ask` | Hỏi đáp ngôn ngữ tự nhiên (confidence threshold) | ✓ |
| GET | `/chat/history` | Lịch sử hội thoại (5 lượt gần nhất) | ✓ |

```jsonc
// POST /chat/ask
{ "question": "Phòng 1.5 triệu gần CTU có wifi?", "session_id": "abc" }
// 200 — confidence cao
{ "answer": "Có 3 phòng phù hợp...", "confidence": "high",
  "sources": [ { "listing_id": 1, "title": "..." } ] }
// 200 — confidence thấp (T8: không bịa)
{ "answer": "Không tìm thấy thông tin phù hợp. Thử từ khóa khác nhé!",
  "confidence": "low", "sources": [] }
```

---

## 6. Risk (`/risk`)

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| GET | `/listings/{id}/risk` | Chi tiết risk_score + risk_reasons[] | 🌐 |

```jsonc
// 200
{ "listing_id": 1, "risk_score": 0.72, "risk_level": "suspicious",
  "risk_reasons": ["Giá thấp hơn 40% so với khu vực", "Không có ảnh thực tế"] }
```

---

## 7. Admin (`/admin`)

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| GET | `/admin/dashboard` | Thống kê tổng quan | Admin |
| GET | `/admin/listings/flagged` | DS tin risk cao / bị report | Admin |
| POST | `/admin/listings/{id}/moderate` | Duyệt / ẩn tin | Admin |
| GET | `/admin/users` | Quản lý người dùng | Admin |
| POST | `/admin/users/{id}/lock` | Khóa tài khoản | Admin |

---

## 8. Crawler (`/crawler`) — đã hiện thực

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| GET | `/crawler/status` | Trạng thái N lần crawl gần nhất (crawl_runs) | Admin |
| POST | `/crawler/run` | Trigger thủ công 1 nguồn (`source`, `mode`) | Admin |

```jsonc
// POST /crawler/run?source=phongtro123&mode=incremental
{ "source": "phongtro123", "mode": "incremental",
  "fetched": 2, "new_count": 12, "updated_count": 3, "expired_count": 0, "error": null }
```

---

## 9. Health — đã hiện thực

| Method | Path | Mô tả | Auth |
|---|---|---|---|
| GET | `/health` | Liveness | 🌐 |
| GET | `/health/deps` | PostGIS + pgvector + Redis | 🌐 |

---

## Phụ lục: trạng thái hiện thực
- ✅ Đã code: `/health`, `/health/deps`, `/crawler/*`.
- ⬜ Chưa code (Sprint 1-4): auth, listings, recommend, matching, chat, risk, admin.
- Khi code, dùng FastAPI auto-docs tại `/docs` (OpenAPI) làm nguồn chính thức; file này là hợp đồng thiết kế.
