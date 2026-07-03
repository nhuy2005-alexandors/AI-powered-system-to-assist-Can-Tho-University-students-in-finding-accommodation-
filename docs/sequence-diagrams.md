# Sequence Diagrams — Trọ CTU

Các sơ đồ tuần tự cho luồng nghiệp vụ chính. Lớp tham chiếu: Router → Service/Repo → Database/External.

## 1. Đăng nhập (Login — Multi-provider)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Next.js Client
    participant RH as Route Handler /api/auth/login
    participant AR as AuthRouter (FastAPI)
    participant Repo as AuthRepo
    participant DB as PostgreSQL
    participant JWT as JWT Security

    U->>FE: Nhập email + mật khẩu
    FE->>RH: POST /api/auth/login (same-origin)
    RH->>AR: POST /auth/login (internal Docker)
    AR->>Repo: get_user_by_email(email)
    Repo->>DB: SELECT users WHERE email
    DB-->>Repo: User | None
    alt User tồn tại
        AR->>Repo: get_identity(user_id, 'local')
        Repo->>DB: SELECT user_identities WHERE user_id + provider='local'
        DB-->>Repo: Identity (secret_hash)
        AR->>AR: bcrypt.verify(password, secret_hash)
        alt Mật khẩu đúng
            AR->>JWT: create_access + create_refresh (user_id, role)
            JWT-->>AR: TokenPair
            AR-->>RH: 200 {access_token, refresh_token}
            RH->>RH: Set httpOnly cookies (access + refresh)
            RH-->>FE: 200 {user}
            FE->>FE: Redirect → /me
        else Sai mật khẩu
            AR-->>RH: 401 "Sai mật khẩu"
            RH-->>FE: 401 {error}
        end
    else Không tồn tại
        AR-->>RH: 401 "Sai email hoặc mật khẩu"
        RH-->>FE: 401 {error}
    end
```

> Token được lưu trong **httpOnly cookie** (chống XSS) bởi Next.js Route Handler — frontend JS không bao giờ chạm token. Access token TTL 15 phút, refresh 30 ngày.

## 2. Crawl Pipeline (Tự động / Thủ công)

```mermaid
sequenceDiagram
    actor S as Scheduler (APScheduler)
    participant PL as Pipeline
    participant FT as Fetcher
    participant PR as Parser
    participant NM as Normalize
    participant GC as Geocoder (Nominatim)
    participant DD as Dedup (content_hash)
    participant Repo as ListingRepo
    participant DB as PostgreSQL + PostGIS

    S->>PL: run_source(source, mode)
    PL->>PL: load_source_config(source.json)
    PL->>FT: get(list_url + page)
    FT->>FT: Rate-limit 1req/5s, rotate UA
    FT-->>PL: HTML
    PL->>PR: parse_list_page(html, config)
    PR-->>PL: RawListing[] (CSS selectors)

    loop Mỗi listing (detail page)
        PL->>FT: get(detail_url)
        FT-->>PL: Detail HTML
        PL->>PR: parse_detail_page(html, config)
        PR-->>PL: DetailData (description, images)
        PL->>PL: merge_detail(raw, detail)
    end

    PL->>NM: normalize(raw) → giá/diện tích/tiện ích
    NM-->>PL: NormalizedListing

    PL->>GC: geocode(address)
    GC-->>PL: (lat, lng, confidence)
    PL->>PL: haversine(lat, lng, CTU) → distance

    PL->>DD: content_hash(SHA-256)
    PL->>Repo: upsert(listing, lat, lng, distance)
    Repo->>DB: INSERT ON CONFLICT (source, source_id) DO UPDATE
    DB-->>Repo: id

    PL->>Repo: mark_expired(source, missed IDs)
    Repo->>DB: UPDATE status='expired' WHERE miss_count ≥ 2
    PL->>Repo: log_crawl_run(stats)
```

> Mỗi nguồn được cấu hình bằng 1 file JSON (`sources/<name>.json`) chứa CSS selectors — thêm nguồn mới không cần sửa code Python. Scheduler chạy: incremental mỗi 5h (trang 1-2), full sweep 3h sáng.

## 3. Tìm kiếm & Lọc

```mermaid
sequenceDiagram
    actor U as User/Guest
    participant FE as Next.js Client
    participant LR as ListingsRouter (FastAPI)
    participant QR as ListingQueryRepo
    participant DB as PostgreSQL + PostGIS

    U->>FE: Nhập từ khóa + chọn bộ lọc
    FE->>LR: GET /listings?q=&min_price=&district=&sort=nearest
    LR->>QR: search(params)
    QR->>QR: build_filters(params) → WHERE clause
    Note over QR: status NOT IN ('expired', 'hidden')<br/>+ price BETWEEN + district + amenities
    QR->>DB: SELECT ... WHERE clauses ORDER BY sort LIMIT size OFFSET
    DB-->>QR: rows
    QR->>QR: _to_out(rows) → ListingOut[]
    QR-->>LR: {total, page, size, items}
    LR-->>FE: 200 JSON
    FE->>FE: Render cards + map pins
```

## 4. Đăng tin UGC + Geocode

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Next.js Client
    participant LR as ListingsRouter (FastAPI)
    participant Auth as get_current_user (JWT)
    participant GC as Geocoder (Nominatim)
    participant WR as ListingWriteRepo
    participant QR as ListingQueryRepo
    participant DB as PostgreSQL + PostGIS

    U->>FE: Điền form đăng tin
    FE->>LR: POST /listings {title, price, area, address, ...}
    LR->>Auth: Verify Bearer token
    Auth-->>LR: UserOut (id, role)
    LR->>GC: geocode(address)
    GC-->>LR: (lat, lng, confidence)
    LR->>LR: haversine(lat, lng, CTU) → distance
    LR->>WR: create(data, user_id, lat, lng, conf, dist)
    WR->>DB: INSERT aggregated_listings (source='user', posted_by=user_id, geom=ST_MakePoint)
    DB-->>WR: new_id
    LR->>QR: get(new_id) → ListingOut
    QR-->>LR: ListingOut
    LR-->>FE: 201 ListingOut
```

## 5. Chatbot RAG

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Next.js Client
    participant CR as ChatRouter (FastAPI)
    participant EMB as Embedding Model
    participant DB as PostgreSQL + pgvector
    participant LLM as Gemini LLM
    participant Mem as Conversation Memory

    U->>FE: Nhập câu hỏi tự nhiên
    FE->>CR: POST /chat/ask {question, session_id}
    CR->>Mem: load_history(session_id, last 5)
    Mem-->>CR: conversation context
    CR->>EMB: embed(question) → query_vector 384-dim
    EMB-->>CR: query_vector
    CR->>DB: SELECT ... ORDER BY embedding_vector <=> query_vector LIMIT K
    DB-->>CR: top-K listings (context documents)
    CR->>LLM: prompt(system + context + history + question)
    LLM-->>CR: answer + confidence
    alt Confidence ≥ 0.65
        CR->>Mem: save(question, answer)
        CR-->>FE: 200 {answer, confidence: "high", sources: [...]}
    else Confidence < 0.65
        CR-->>FE: 200 {answer: "Không tìm thấy...", confidence: "low", sources: []}
    end
```

> Confidence thresholding (T8): hệ thống **không bịa** — nếu không tìm thấy thông tin đáng tin cậy, trả lời fallback thay vì hallucinate. Conversation memory giữ 5 lượt gần nhất cho multi-turn context.

## 6. Tìm bạn ở ghép (Roommate Matching)

```mermaid
sequenceDiagram
    actor A as User A
    actor B as User B
    participant FE as Next.js Client
    participant MR as MatchingRouter (FastAPI)
    participant DB as PostgreSQL + pgvector

    A->>FE: Điền hồ sơ 6 câu
    FE->>MR: POST /matching/profile {sleep_time, cleanliness, smoke, ...}
    MR->>MR: encode → matching_vector 384-dim
    MR->>DB: UPSERT roommate_profiles
    DB-->>MR: ok

    A->>FE: Xem danh sách tương thích
    FE->>MR: GET /matching/candidates
    MR->>DB: SELECT ... WHERE matching_vector <=> A.vector, score ≥ 0.7
    DB-->>MR: candidates[]
    MR-->>FE: 200 {items: [{user_id, name, score, habits}]}

    A->>FE: Gửi lời mời
    FE->>MR: POST /matching/invite {to_user: B.id}
    MR->>DB: INSERT match_requests (from=A, to=B, status='pending')
    DB-->>MR: ok

    B->>FE: Chấp nhận lời mời
    FE->>MR: POST /matching/invite/{id}/respond {accept: true}
    MR->>DB: UPDATE match_requests SET status='accepted'
    MR->>DB: SELECT phone, email FROM users WHERE id IN (A, B)
    DB-->>MR: contact info
    MR-->>FE: 200 {contact: {phone, email}} (lộ 2 chiều)
```

> Liên hệ (phone/email) chỉ lộ khi **cả hai bên** đồng ý — bảo vệ quyền riêng tư sinh viên. Weighted Cosine Similarity threshold 0.7 lọc bỏ ứng viên không tương thích.
