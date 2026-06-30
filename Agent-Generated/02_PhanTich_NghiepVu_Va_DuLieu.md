# 📑 TÀI LIỆU 2: PHÂN TÍCH NGHIỆP VỤ & CHIẾN LƯỢC DỮ LIỆU
**Đề tài:** Xây dựng hệ thống tổng hợp và gợi ý nhà trọ ứng dụng AI hỗ trợ sinh viên ĐH Cần Thơ

---

## 1. 👥 CÁC TÁC NHÂN (ACTORS)

1. **Khách (Guest):** Xem tin, tìm kiếm, lọc — chưa cần đăng nhập.
2. **Người dùng (User — Sinh viên/Bất kỳ ai):** Đăng nhập để dùng AI gợi ý, matching bạn ghép, chatbot, lưu tin yêu thích, đăng tin, đánh giá.
3. **Admin:** Quản trị nội dung, kiểm duyệt, quản lý cấu hình crawler, xem dashboard thống kê.
4. **Hệ thống (System Actor):** Crawler tự động, AI pipeline, Scheduled Jobs.

---

## 2. 📋 DANH SÁCH CHỨC NĂNG ĐẦY ĐỦ

### ═══════════════════════════════════════
### NHÓM A — NỀN TẢNG WEB CƠ BẢN (Baseline)
### ═══════════════════════════════════════

#### A1. Authentication & Authorization (Xác thực & Phân quyền)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| A1.1 | Đăng ký tài khoản | Email + Mật khẩu, xác thực OTP qua email | Guest |
| A1.2 | Đăng nhập | Email/Password + JWT Token | Guest |
| A1.3 | Đăng nhập Google OAuth | "Đăng nhập bằng Google" (OAuth 2.0) — nhanh gọn cho sinh viên | Guest |
| A1.4 | Quên mật khẩu | Gửi link đặt lại mật khẩu qua email | Guest |
| A1.5 | Quản lý hồ sơ cá nhân | Đổi avatar, tên, SĐT, mật khẩu | User |
| A1.6 | Phân quyền RBAC | 3 role: Guest / User / Admin — Middleware kiểm tra trước mỗi API | System |

#### A2. Tìm kiếm & Lọc (Search & Filter)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| A2.1 | Tìm kiếm text | Thanh search bar: nhập địa chỉ, tên đường, tên khu vực | Guest |
| A2.2 | Lọc đa tiêu chí | Khoảng giá (slider), Diện tích, Quận/Phường, Tiện ích (checkbox), Khoảng cách đến CTU | Guest |
| A2.3 | Sắp xếp kết quả | Theo: Giá tăng/giảm, Mới nhất, Gần CTU nhất, Điểm an sinh cao nhất | Guest |
| A2.4 | Tìm trên bản đồ | Hiển thị pin nhà trọ trên bản đồ Leaflet/OSM, click pin → xem chi tiết | Guest |
| A2.5 | Tìm theo bán kính | Vẽ vòng tròn trên bản đồ → chỉ hiện nhà trọ trong bán kính đó | Guest |

#### A3. Xem chi tiết & Tương tác
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| A3.1 | Trang chi tiết nhà trọ | Ảnh (gallery/carousel), Giá, Diện tích, Tiện ích, Bản đồ mini, Badge rủi ro, Nguồn gốc + link gốc, Thời gian cập nhật lần cuối | Guest |
| A3.2 | Lưu tin yêu thích | Bookmark phòng trọ → Xem lại trong "Danh sách yêu thích" | User |
| A3.3 | So sánh phòng trọ | Chọn 2-3 phòng → Bảng so sánh cạnh nhau (giá, diện tích, tiện ích, khoảng cách) | User |
| A3.4 | Chia sẻ tin | Copy link / Chia sẻ qua mạng xã hội | Guest |
| A3.5 | Báo cáo tin sai | Nút "Báo cáo" → Chọn lý do (Sai giá, Tin cũ, Lừa đảo) → Gửi cho Admin | User |

#### A4. Quản lý tin đăng (UGC — User Generated Content)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| A4.1 | Đăng tin mới | Form đăng tin: Tiêu đề, Giá, Diện tích, Địa chỉ, Ảnh (upload), Mô tả, Tiện ích | User |
| A4.2 | Chỉnh sửa/Xóa tin | Quản lý các tin đã đăng của mình | User |
| A4.3 | Kiểm duyệt tin UGC | Tin UGC mới phải qua AI Risk Check → Nếu risk > ngưỡng → Chờ Admin duyệt | System + Admin |

#### A5. Thông báo (Notifications)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| A5.1 | Thông báo tin mới | Khi crawler tìm thấy tin mới khớp tiêu chí đã lưu → Push notification / Email | User |
| A5.2 | Thông báo matching | Khi có bạn ghép mới tương thích > 70% → Thông báo | User |
| A5.3 | Thông báo admin | Khi crawler gặp lỗi, hoặc có tin bị report nhiều → Alert cho admin | Admin |

---

### ═══════════════════════════════════════
### NHÓM B — TÍNH NĂNG AI (Lõi nghiên cứu)
### ═══════════════════════════════════════

#### B1. Gợi ý nhà trọ cá nhân hóa (AI Recommendation)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| B1.1 | Onboarding quiz | 3 câu hỏi nhanh (Ngân sách, Khoảng cách, Tiện ích) khi đăng ký lần đầu → Tạo vector khởi tạo | User |
| B1.2 | Gợi ý "Dành cho bạn" | Trang chủ hiển thị Top-10 phòng phù hợp nhất dựa trên profile + hành vi | User |
| B1.3 | Implicit feedback | Ghi nhận hành vi ẩn: thời gian xem, bookmark, click link nguồn → Cập nhật vector | System |
| B1.4 | Tab "Khám phá" | 80% gợi ý phù hợp + 20% phòng ngẫu nhiên (Epsilon-Greedy) tránh Filter Bubble | User |

#### B2. Matching bạn ở ghép (Roommate Matching)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| B2.1 | Điền hồ sơ ở ghép | Form câu hỏi tình huống (Forced Choice) về lối sống | User |
| B2.2 | Xem danh sách bạn ghép | Danh sách người tương thích, sắp xếp theo Matching Score | User |
| B2.3 | Gửi lời mời kết nối | Gửi tin nhắn giới thiệu cho người muốn ghép | User |

#### B3. Chatbot trợ lý ảo (RAG LLM)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| B3.1 | Hỏi bằng ngôn ngữ tự nhiên | "Tìm phòng 1.5 triệu gần CTU có wifi" → Chatbot trả lời kèm danh sách phòng | User |
| B3.2 | Hội thoại nhiều lượt | Nhớ ngữ cảnh 5 lượt gần nhất (Conversation Memory) | User |
| B3.3 | Từ chối khi không biết | Confidence Thresholding — Không bịa khi không có dữ liệu | System |

#### B4. Cảnh báo rủi ro (Risk Detection)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| B4.1 | Badge rủi ro trên mỗi tin | Hiển thị: "✅ An toàn" / "⚠️ Cần kiểm chứng" / "🔴 Nghi vấn" | Guest |
| B4.2 | Giải thích lý do | Click badge → Popup: "Giá thấp hơn 40% so với khu vực" hoặc "Không có ảnh thực tế" | Guest |

---

### ═══════════════════════════════════════
### NHÓM C — HỆ THỐNG & ADMIN
### ═══════════════════════════════════════

#### C1. Data Pipeline (Crawler & Processing)
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| C1.1 | Crawler tự động | Scrapy/Playwright crawl định kỳ 6-12h từ Phongtro123, Chotot, Mogi | System |
| C1.2 | NLP chuẩn hóa | Trích xuất giá, diện tích, tiện ích từ mô tả text tự do | System |
| C1.3 | Deduplication | MinHash + LSH phát hiện tin trùng lặp cross-platform | System |
| C1.4 | Geocoding đa tầng | Chuyển địa chỉ text → Tọa độ GPS (xem Tài liệu 4 - Bài toán 6) | System |
| C1.5 | Tính khoảng cách POI | PostGIS tính khoảng cách đến đồn CA, bệnh viện, trạm bus | System |
| C1.6 | Embedding & Indexing | Nhúng vector cho RAG chatbot sau mỗi lần cập nhật dữ liệu | System |

#### C2. Admin Dashboard
| ID | Chức năng | Mô tả | Quyền |
|---|---|---|---|
| C2.1 | Dashboard tổng quan | Tổng tin, tin mới hôm nay, tin bị report, crawler status | Admin |
| C2.2 | Quản lý tin bị flagged | Danh sách tin risk cao / bị report → Duyệt / Ẩn / Xóa | Admin |
| C2.3 | Cấu hình crawler | Bật/tắt nguồn, đổi tần suất, xem log crawl gần nhất | Admin |
| C2.4 | Quản lý người dùng | Xem danh sách, khóa tài khoản vi phạm | Admin |

---

## 3. 📡 CHIẾN LƯỢC THU THẬP DỮ LIỆU (DATA STRATEGY)

Áp dụng chiến lược "3 Mũi nhọn + 1 Nền tảng không gian":
1. **Dữ liệu Không gian (Spatial Data - Chạy 1 lần):** Dùng Overpass API (OpenStreetMap) tải dữ liệu tọa độ tĩnh của các đồn công an, bệnh viện, trạm xe buýt quanh CTU. Lưu vào DB để tính toán nội bộ (tiết kiệm chi phí API Google Maps).
2. **Giai đoạn 1 (Seed Data - Tháng 1):** Khảo sát thực địa, điền Google Form để lấy 100-200 dòng dữ liệu siêu sạch làm Ground Truth huấn luyện AI.
3. **Giai đoạn 2 (Crawler - Tháng 2, 3):** Khởi chạy Scrapy/Playwright crawler lấy dữ liệu định kỳ. Giải quyết triệt để bài toán Cold-Start.
4. **Giai đoạn 3 (Community/UGC - Tháng 4, 5):** Mở tính năng cho sinh viên đăng tin mới và báo cáo tin sai lệch.

> **Lưu ý phạm vi:** Hệ thống cung cấp dữ liệu ở mức **gần thời gian thực (near real-time)** với chu kỳ cập nhật 6–12 giờ. Việc xác nhận tình trạng phòng trống cụ thể **nằm ngoài phạm vi** đề tài — hệ thống chỉ hiển thị thời gian cập nhật lần cuối và dẫn link nguồn gốc để người dùng tự xác nhận.

---

## 4. 🗄️ CẤU TRÚC DATABASE CHÍNH (LƯỢC ĐỒ)

```sql
-- ═══ DỮ LIỆU NHÀ TRỌ ═══
CREATE TABLE aggregated_listings (
    id              SERIAL PRIMARY KEY,
    title           TEXT,
    price           INTEGER,
    area            REAL,
    address         TEXT,
    district        VARCHAR(50),
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION,
    images          TEXT[],              -- Mảng URL ảnh
    description     TEXT,
    
    -- Nguồn gốc
    source          VARCHAR(30),         -- 'phongtro123', 'chotot', 'ugc'
    source_url      TEXT,                -- NULL nếu UGC
    source_id       TEXT,
    posted_by       INTEGER REFERENCES users(id),  -- NULL nếu crawl
    
    -- AI sinh ra & Không gian
    parsed_amenities  JSONB,
    risk_score        REAL DEFAULT 0,
    risk_reasons      TEXT[],            -- ["Giá thấp bất thường", "Không có ảnh"]
    distance_to_ctu   REAL,
    distance_to_police REAL,
    distance_to_hospital REAL,
    geocode_confidence VARCHAR(10),      -- 'high'|'medium'|'low'|'failed'
    embedding_vector  VECTOR(384),
    
    -- Thời gian
    first_seen      TIMESTAMP DEFAULT NOW(),
    last_seen       TIMESTAMP DEFAULT NOW(),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ═══ NGƯỜI DÙNG ═══
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   TEXT,                -- NULL nếu dùng OAuth
    name            VARCHAR(100),
    avatar_url      TEXT,
    phone           VARCHAR(20),
    role            VARCHAR(10) DEFAULT 'user',  -- 'guest'|'user'|'admin'
    provider        VARCHAR(20) DEFAULT 'local', -- 'local'|'google'
    
    -- Preference cho AI gợi ý
    budget_min      INTEGER,
    budget_max      INTEGER,
    preferred_district VARCHAR(50),
    preferred_amenities JSONB,
    preference_vector VECTOR(384),       -- Vector profile cho Recommendation
    
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ═══ DỮ LIỆU KHÔNG GIAN (POI) ═══
CREATE TABLE poi_locations (
    id              SERIAL PRIMARY KEY,
    name            TEXT,
    poi_type        VARCHAR(30),         -- 'police', 'hospital', 'bus_stop', 'market'
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION
);

-- ═══ TIN YÊU THÍCH ═══
CREATE TABLE favorites (
    user_id         INTEGER REFERENCES users(id),
    listing_id      INTEGER REFERENCES aggregated_listings(id),
    created_at      TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, listing_id)
);

-- ═══ BÁO CÁO TIN SAI ═══
CREATE TABLE reports (
    id              SERIAL PRIMARY KEY,
    listing_id      INTEGER REFERENCES aggregated_listings(id),
    reporter_id     INTEGER REFERENCES users(id),
    reason          VARCHAR(50),         -- 'wrong_price'|'expired'|'scam'|'other'
    note            TEXT,
    status          VARCHAR(20) DEFAULT 'pending', -- 'pending'|'reviewed'|'dismissed'
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ═══ HỒ SƠ Ở GHÉP ═══
CREATE TABLE roommate_profiles (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id),
    sleep_time      INTEGER,             -- 0: Sớm, 1: Bình thường, 2: Cú đêm
    cleanliness     INTEGER,             -- 1-5
    smoke           BOOLEAN,
    noise_tolerance INTEGER,             -- 1-5
    gender_pref     INTEGER,             -- 0: Không quan tâm, 1: Nam, 2: Nữ
    bio             TEXT,
    matching_vector VECTOR(384),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ═══ IMPLICIT FEEDBACK ═══
CREATE TABLE user_interactions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    listing_id      INTEGER REFERENCES aggregated_listings(id),
    action          VARCHAR(20),         -- 'view'|'bookmark'|'click_source'|'click_phone'
    duration_ms     INTEGER,             -- Thời gian xem (ms)
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 5. 📊 MA TRẬN CHỨC NĂNG THEO GIAI ĐOẠN PHÁT TRIỂN

| Giai đoạn | Chức năng triển khai | Mục tiêu |
|---|---|---|
| **Sprint 1 (Tháng 1)** | A1 (Auth), A2 (Search/Filter), A3.1 (Chi tiết), C1.1-C1.2 (Crawler cơ bản) | Có trang web chạy được với dữ liệu thật |
| **Sprint 2 (Tháng 2)** | C1.3-C1.6 (Pipeline hoàn chỉnh), A2.4 (Bản đồ), B4 (Risk Badge) | Data pipeline + Bản đồ + Cảnh báo rủi ro |
| **Sprint 3 (Tháng 3)** | B1 (Gợi ý AI), A3.2 (Yêu thích), B1.3 (Implicit Feedback) | Module AI gợi ý chạy thực tế |
| **Sprint 4 (Tháng 4)** | B3 (Chatbot RAG), B2 (Matching), A4 (UGC) | Chatbot + Matching + Cho phép SV đăng tin |
| **Sprint 5 (Tháng 5)** | A5 (Notifications), A3.3 (So sánh), C2 (Admin Dashboard) | Hoàn thiện trải nghiệm |
| **Sprint 6 (Tháng 6)** | Testing, Đánh giá, Viết báo cáo, Chuẩn bị bảo vệ | Nghiệm thu |
