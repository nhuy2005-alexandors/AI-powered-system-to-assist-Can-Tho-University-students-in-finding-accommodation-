# Trọ CTU — Hệ thống tổng hợp & gợi ý nhà trọ AI (THS2026-66)

Monorepo Sprint 0 scaffold. Stack theo `Document/Technical_Roadmap.md` (P1: chi phí 0đ, free-tier).

## Cấu trúc

```
apps/
  api/      FastAPI (nghiệp vụ + AI + crawler) — Python 3.12
  web/      Next.js 14 + Tailwind (frontend)
infra/
  db/       PostgreSQL 16 + PostGIS + pgvector (Dockerfile + init.sql + migrations/)
docker-compose.yml   db + redis + api + web
```

## Tài liệu (`Document/` + `Agent-Generated/`)

| Tài liệu | Nội dung |
|---|---|
| `SRS.md` | Đặc tả yêu cầu (IEEE 830): FR + NFR + acceptance |
| `API_Specification.md` | Đặc tả API: 9 nhóm endpoint |
| `Data_Dictionary.md` | Từ điển dữ liệu 8 bảng + quan hệ |
| `Test_Plan.md` | Kế hoạch kiểm thử + test case |
| `Deployment_Guide.md` | Hướng dẫn triển khai (local/staging/prod) |
| `Technical_Roadmap.md` | Giải pháp kỹ thuật T1-T11 + DoD |
| `Sprint_Plan.md` | Kế hoạch 6 sprint |
| `Agent-Generated/02..05` | Nghiệp vụ, thiết kế AI, bài toán khó, use case |

## Sơ đồ (`Diagrams/archify/`, HTML mở browser)

`01_Architecture` · `02_UseCase` · `03..06` workflow (Crawler/Chatbot/Matching/TìmKiếm) · `07_ERD` · `08_Sequence_Login` · `09_Sequence_RAG`.
Sửa: edit `.json` nguồn → `node ~/.claude/skills/archify/renderers/<mode>/render-<mode>.mjs <in>.json <out>.html`.

## Chạy local

Yêu cầu: Docker Desktop (có `docker compose`).

```bash
cp .env.example .env
docker compose up --build
```

Sau khi 4 service healthy:

- Web:  http://localhost:3000
- API:  http://localhost:8000/health  ·  /health/deps  ·  /docs
- DB:   localhost:5432 (nckh/nckh)
- Redis: localhost:6379

`GET /health/deps` xác minh PostGIS + pgvector + Redis hoạt động.

## DoD Sprint 0.4

- [ ] `docker compose up` khởi động cả 4 service không lỗi
- [ ] `/health/deps` trả `postgis` + `pgvector` = ok
- [ ] Web render trạng thái backend health

## Ghi chú

- Hot-reload API: `docker compose watch` (sync `apps/api/app`).
- Chưa cài Docker trên máy hiện tại → cần cài Docker Desktop để verify runtime.
