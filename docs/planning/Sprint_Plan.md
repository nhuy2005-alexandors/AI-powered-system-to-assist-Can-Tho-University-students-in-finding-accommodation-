# 📅 SPRINT PLAN — THS2026-66

**Đề tài:** Hệ thống tổng hợp & gợi ý nhà trọ AI — hỗ trợ SV ĐH Cần Thơ
**Thời gian:** 5/2026 – 10/2026 (6 sprint × 1 tháng)
**Đội:** Phú (chủ nhiệm/AI+data), Phúc (phân tích/matching), Lợi (backend/frontend), Bảo (UI/frontend), Huy (data/spatial)
**Liên kết:** thách thức kỹ thuật T1–T11 xem `Technical_Roadmap.md`

**Trạng thái:** ⬜ chưa bắt đầu · 🟦 đang làm · ✅ xong · ⚠️ chặn

---

## SPRINT 0 — Tháng 5/2026 · Khảo sát + Setup
**Mục tiêu:** Có ground-truth data + môi trường dev chạy được.

| # | Task | Người | DoD | Liên kết | TT |
|---|---|---|---|---|---|
| 0.1 | Google Form khảo sát (15–20 câu) | Phúc | Form live, target N=200 | — | ⬜ |
| 0.2 | Phân phát form (Zalo/FB SV CTU) | All | 150–200 responses | — | ⬜ |
| 0.3 | Phân tích thống kê (pandas) | Phú | Báo cáo nhu cầu .pdf | — | ⬜ |
| 0.4 | Repo Git + docker-compose (PG+Redis+FastAPI+Next) | Lợi | `docker compose up` chạy | — | ⬜ |
| 0.5 | Tải POI OSM Overpass (CA/BV/bus Ninh Kiều) | Huy | `poi_locations` ~500 rows | T3 | ⬜ |
| 0.6 | Seed ward_centroids 13 phường Ninh Kiều | Huy | bảng centroid đủ | T2 | ⬜ |
| 0.7 | Manual seed 100 phòng ground-truth | Bảo+all | 100 listing JSON sạch | T4,T5 | ⬜ |

**Gate S0:** form ≥150 resp · docker chạy · 100 listing + 500 POI trong DB.

---

## SPRINT 1 — Tháng 6/2026 · Crawler + DB + Auth
**Mục tiêu:** Pipeline data + web baseline.

| # | Task | Người | DoD | Liên kết | TT |
|---|---|---|---|---|---|
| 1.1 | Scrapy crawler Phongtro123 (selectors JSON) | Phú | 1000 listing/run, rate-limit | T1 | ⬜ |
| 1.2 | Crawler Chotot + Mogi (plugin riêng) | Phú | 2 plugin JSON | T1 | ⬜ |
| 1.3 | Health check + alert Telegram | Phú | alert khi <10 tin | T1 | ⬜ |
| 1.4 | Raw HTML backup trước parse | Phú | re-parse offline OK | T1 | ⬜ |
| 1.5 | NLP chuẩn hóa giá/DT/amenities | Phú | ≥85% acc/100 mẫu | T1 | ⬜ |
| 1.6 | Geocoding 3 tầng | Huy | confidence field hoạt động | T2 | ⬜ |
| 1.7 | MinHash+LSH dedup (datasketch) | Huy | recall ≥90% | T4 | ⬜ |
| 1.8 | PostGIS distance CTU+POI (trigger) | Huy | tính khi insert | T3 | ⬜ |
| 1.9 | Next.js skeleton + Tailwind + JWT Auth (A1) | Lợi+Bảo | đăng ký/login + OAuth Google | — | ⬜ |
| 1.10 | API listing CRUD + search/filter (A2) | Lợi | REST + Swagger | — | ⬜ |

**Gate S1:** crawl ≥5000 → dedup ~3000 unique · ≥80% có toạ độ ≥medium · auth + search chạy.

---

## SPRINT 2 — Tháng 7/2026 · UI Search + Map + Risk + Freshness
**Mục tiêu:** User dùng được core; data có nhãn tin cậy.

| # | Task | Người | DoD | Liên kết | TT |
|---|---|---|---|---|---|
| 2.1 | List view + detail page (A3.1) | Bảo | responsive, gallery | — | ⬜ |
| 2.2 | Map view Leaflet + cluster pins (A2.4) | Lợi | click pin → popup | T3 | ⬜ |
| 2.3 | Search/filter UI + bán kính (A2.1–A2.5) | Bảo | slider giá, checkbox, radius | — | ⬜ |
| 2.4 | Bookmark + so sánh (A3.2,A3.3) | Bảo | bảng so sánh 3 cột | — | ⬜ |
| 2.5 | Risk module: IsolationForest + rule 5 lớp | Phú | score + reasons[] | T10 | ⬜ |
| 2.6 | Risk badge UI (B4.1) | Lợi | 3 mức + popup lý do | T10 | ⬜ |
| 2.7 | Freshness score + status + 1-click report | Lợi | nhãn stale tự động | T11 | ⬜ |

**Gate S2:** demo search→detail→badge đúng/100 mẫu · tin >30 ngày gắn stale.

---

## SPRINT 3 — Tháng 8/2026 · Recommendation + Roommate Matching
**Mục tiêu:** AI module 2+3 + evaluation.

| # | Task | Người | DoD | Liên kết | TT |
|---|---|---|---|---|---|
| 3.1 | Onboarding Quiz → preference_vector (B1.1) | Phú | vector 384-dim | T5 | ⬜ |
| 3.2 | Content-Based + Cosine (B1.2) | Phú | `/api/recommend/:id` | T5 | ⬜ |
| 3.3 | Implicit feedback tracker (B1.3) | Lợi | `user_interactions` ghi | T5 | ⬜ |
| 3.4 | Tab Khám phá ε-greedy 80/20 (B1.4) | Phú | flag bật/tắt | T6 | ⬜ |
| 3.5 | Roommate form Forced Choice 6 câu (B2.1a) | Bảo | matching_vector | T7 | ⬜ |
| 3.6 | Weighted Cosine matching (B2.1–B2.3) | Phú | threshold 0.7, topK=20 | T7 | ⬜ |
| 3.7 | Eval: Precision@10, NDCG@10, ILS | Phú | notebook + chart | T5,T6 | ⬜ |

**Gate S3:** Precision@10 ≥0.6 · ILS ≤0.7 (30 user-mock).

---

## SPRINT 4 — Tháng 9/2026 · Chatbot RAG + UGC + Admin
**Mục tiêu:** AI module 4 + tính năng còn lại.

| # | Task | Người | DoD | Liên kết | TT |
|---|---|---|---|---|---|
| 4.1 | Indexing e5-small → pgvector (auto re-index) | Phú | re-index sau crawl | T8 | ⬜ |
| 4.2 | RAG retrieval + Gemini 2.0 Flash + threshold 0.65 | Phú | từ chối khi <0.65 | T8 | ⬜ |
| 4.3 | Conversation Memory 5 lượt | Phú | multi-turn pass | T9 | ⬜ |
| 4.4 | Chatbot UI floating widget (B3.1) | Bảo | streaming | — | ⬜ |
| 4.5 | RAGAS eval (Faithfulness, AnsRel) | Phú | ≥0.7 / ≥0.75, 50 Q&A | T8 | ⬜ |
| 4.6 | UGC đăng tin + AI Risk check (A4) | Lợi | pending nếu risk cao | T10 | ⬜ |
| 4.7 | Admin Dashboard (C2.1–C2.4) | Bảo | stats+duyệt+cấu hình crawler | — | ⬜ |
| 4.8 | Email notif tin mới phù hợp (A5.1) | Lợi | cron 8h sáng | T5 | ⬜ |

**Gate S4:** chatbot 20 câu test · 0 hallucination (manual) · UGC workflow chạy.

---

## SPRINT 5 — Tháng 10/2026 · Test + Deploy + Báo cáo
**Mục tiêu:** Nghiệm thu.

| # | Task | Người | Tuần | TT |
|---|---|---|---|---|
| 5.1 | Unit test backend ≥60% coverage | Phú/Lợi | W1 | ⬜ |
| 5.2 | Pen test cơ bản (OWASP ZAP: SQLi,XSS) | Lợi | W1 | ⬜ |
| 5.3 | User testing 20 SV + SUS survey | All | W2 | ⬜ |
| 5.4 | Deploy prod (VPS Ubuntu+Nginx+Let's Encrypt) | Phú | W2 | ⬜ |
| 5.5 | Báo cáo toàn văn 40–60 trang | Phú+all | W1–W3 | ⬜ |
| 5.6 | Tóm tắt 5–10 trang | Phú | W3 | ⬜ |
| 5.7 | Video demo 3–5 phút | Bảo+Lợi | W3 | ⬜ |
| 5.8 | Slide bảo vệ + tổng dợt | All | W4 | ⬜ |
| 5.9 | Nghiệm thu hội đồng | All | W4 | ⬜ |

**Gate S5:** prod live · báo cáo+tóm tắt+clip nộp · nghiệm thu pass.

---

## TỔNG QUAN METRIC (chốt nghiệm thu)

| Module | Metric | Ngưỡng |
|---|---|---|
| Crawler | uptime 7 ngày | không block |
| Geocoding | %confidence ≥medium | ≥80% |
| Dedup | recall / false-merge | ≥90% / ≤5% |
| Recommendation | P@10 / NDCG@10 / ILS | ≥0.6 / ≥0.65 / ≤0.7 |
| Roommate | MAE feedback | ≤1.5/5 |
| Chatbot | Faithfulness / AnsRel | ≥0.7 / ≥0.75 |
| Risk | recall scam | ≥85% |

---

## GHI CHÚ VẬN HÀNH

- Overlap nhân sự GĐ2↔GĐ5 trong Thuyết minh → resolved bằng sprint tách rời ở đây.
- Hạ tầng = free tier (Vercel/Render + Supabase PG + Gemini free + OSM). Sau nghiệm thu muốn duy trì → ~$10/tháng VPS (ngoài phạm vi).
- Cập nhật cột TT cuối mỗi sprint. Eval notebook lưu `NCKH/eval/`.
