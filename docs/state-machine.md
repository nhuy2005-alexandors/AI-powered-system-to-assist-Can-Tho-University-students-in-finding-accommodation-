# State Machine Diagrams — Trọ CTU

## 1. Vòng đời Tin đăng (Listing)

Quy tắc cài đặt trong `ListingWriteRepo` (Backend) + Crawler pipeline. Mọi chuyển trạng thái ngoài các cạnh hợp lệ bị từ chối.

```mermaid
stateDiagram-v2
    [*] --> active: Crawler upsert / User đăng tin (UGC)

    active --> expired: miss_count ≥ 2 (Crawler không thấy lại 2 lần)
    active --> flagged: risk_score > ngưỡng / User báo cáo
    active --> hidden: Chủ tin xóa (soft-delete)

    flagged --> active: Admin duyệt (moderate → approve)
    flagged --> hidden: Admin ẩn (moderate → hide)

    expired --> active: Crawler thấy lại (re-upsert, reset miss_count)

    active --> [*]
    hidden --> [*]

    note right of active
        Trạng thái mặc định.
        Xuất hiện trong tìm kiếm.
    end note
    note right of expired
        Tin cũ mà crawler không thấy lại.
        Ẩn khỏi tìm kiếm, giữ data.
    end note
    note right of flagged
        Risk cao hoặc bị báo cáo.
        Chờ Admin kiểm duyệt.
    end note
    note right of hidden
        Chủ tin tự ẩn hoặc Admin ẩn.
        Trạng thái cuối (soft-delete).
    end note
```

**Bảng chuyển trạng thái hợp lệ:**

| Từ \ Đến | active | expired | flagged | hidden |
|-----------|:------:|:-------:|:-------:|:------:|
| active    | — | ✅ | ✅ | ✅ |
| expired   | ✅ | — | ❌ | ❌ |
| flagged   | ✅ | ❌ | — | ✅ |
| hidden    | ❌ | ❌ | ❌ | — |

> `hidden` là trạng thái cuối — tin bị soft-delete không phục hồi tự động. `expired` có thể trở lại `active` nếu crawler phát hiện tin xuất hiện lại trên nguồn. Nguyên tắc P2: **Không xóa dữ liệu hợp lệ**, chỉ ẩn.

---

## 2. Vòng đời Báo cáo (Report)

Cài đặt trong Report workflow. Admin kiểm duyệt từ dashboard.

```mermaid
stateDiagram-v2
    [*] --> pending: User gửi báo cáo (POST /listings/{id}/report)

    pending --> reviewed: Admin xác nhận vi phạm → ẩn/flag listing
    pending --> dismissed: Admin từ chối (không vi phạm)

    reviewed --> [*]
    dismissed --> [*]

    note right of pending
        Báo cáo mới, chờ Admin xem.
        Listing tạm giữ trạng thái hiện tại.
    end note
    note right of reviewed
        Vi phạm xác nhận.
        Listing bị moderate (flag/hide).
    end note
```

---

## 3. Vòng đời Lời mời Ở ghép (Match Request)

Cài đặt trong Matching module. Lời mời 1 chiều, kết quả 2 chiều.

```mermaid
stateDiagram-v2
    [*] --> pending: User A gửi lời mời (POST /matching/invite)

    pending --> accepted: User B chấp nhận
    pending --> rejected: User B từ chối

    accepted --> [*]
    rejected --> [*]

    note right of pending
        B chưa phản hồi.
        A không thấy liên hệ B.
    end note
    note right of accepted
        Lộ liên hệ 2 chiều.
        A thấy phone/email B, B thấy A.
    end note
    note right of rejected
        Kết thúc. Không lộ liên hệ.
        A có thể gửi lại (UNIQUE constraint chặn trùng).
    end note
```

---

## 4. Vòng đời Freshness (Độ tươi dữ liệu)

Logic scoring tự động trong Crawler pipeline. Không phải state machine thuần túy mà là continuous scoring.

```mermaid
stateDiagram-v2
    [*] --> Fresh: Crawler thấy lần đầu (first_seen = now, freshness = 1.0)

    Fresh --> Fresh: Crawler thấy lại → last_seen = now, miss_count = 0, freshness = 1.0
    Fresh --> Stale: Crawler không thấy → miss_count++, freshness giảm
    Stale --> Stale: Vẫn không thấy → miss_count++, freshness tiếp tục giảm
    Stale --> Fresh: Crawler thấy lại → reset miss_count, freshness = 1.0
    Stale --> Expired: miss_count ≥ 2 → status = 'expired'
    Expired --> Fresh: Crawler thấy lại (re-upsert) → status = 'active', reset

    note right of Fresh
        freshness_score: 0.8 - 1.0
        Hiện badge "Cập nhật gần đây"
    end note
    note right of Stale
        freshness_score: 0.3 - 0.7
        Hiện badge "X ngày trước"
    end note
    note right of Expired
        freshness_score: < 0.3
        Ẩn khỏi kết quả tìm kiếm
    end note
```

---

## 5. Vòng đời Crawl Run

Mỗi lần chạy crawler ghi 1 bản ghi `crawl_runs` để monitoring.

```mermaid
stateDiagram-v2
    [*] --> Running: Trigger (scheduler hoặc manual POST /crawler/run)

    Running --> Success: Pipeline hoàn tất (error = NULL)
    Running --> Failed: Pipeline gặp lỗi (error = message)

    Success --> [*]
    Failed --> [*]

    note right of Running
        started_at = now()
        fetched đếm tăng dần
    end note
    note right of Success
        finished_at = now()
        Ghi: new_count, updated_count, expired_count
    end note
    note right of Failed
        finished_at = now()
        error = lý do (403/timeout/parse fail)
        < 10 tin mới → alert Admin
    end note
```

> Health check: nếu `new_count < 10` trong 1 lần crawl full → cảnh báo Admin có thể nguồn bị chặn hoặc layout đổi.
