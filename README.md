# Trọ CTU — Hệ thống tổng hợp & gợi ý nhà trọ AI

Full-stack hệ thống tìm nhà trọ: **FastAPI + PostgreSQL/PostGIS/pgvector** backend, **Next.js 14 + Tailwind** frontend, **Docker Compose** orchestration.

## Kiến trúc

```
├── apps/
│   ├── api/             # FastAPI (nghiệp vụ + AI + crawler) — Python 3.12
│   └── web/             # Next.js 14 + Tailwind (frontend)
├── infra/
│   └── db/              # PostgreSQL 16 + PostGIS + pgvector (Dockerfile + migrations)
├── eval/                # Notebook + script đánh giá mô hình AI (metrics, NDCG, RAGAS)
├── docs/                # Tài liệu kỹ thuật (SRS, API spec, ERD, use case, test plan)
├── Diagrams/            # Sơ đồ kiến trúc, workflow, sequence (HTML interactive)
├── docker-compose.yml   # db + redis + api + web
└── .github/workflows/   # CI: build + test backend/frontend
```

## Chức năng

Crawler tự động (4 nguồn: phongtro123, tromoi, mogi, bds123) · Geocoding tự động (tọa độ + khoảng cách tới ĐH Cần Thơ) · UGC đăng tin (CRUD + soft-delete) · Auth multi-provider (local/Google/CTU SSO) · JWT + httpOnly cookie · RBAC (guest/user/admin) · AI gợi ý nhà trọ · RAG Chatbot.

## Yêu cầu

- Docker Desktop (có `docker compose`)

## Chạy

```bash
cp .env.example .env
docker compose up --build
```

Sau khi 4 service healthy:

- **Frontend:** http://localhost:3000
- **API Swagger:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health/deps (PostGIS + pgvector + Redis)
- **DB:** localhost:5432 (nckh/nckh)

## Test

```bash
# Copy tests vào container và chạy pytest
docker compose exec -T api python -m pytest -v
```

## CI/CD

`.github/workflows/ci.yml` chạy khi push/PR vào `main`: build + test backend (Docker + pytest), build frontend (tsc + next build).

## Tài liệu

Xem thư mục [`docs/`](docs/): SRS, API Specification, Data Dictionary, Test Plan, Sprint Plan, Technical Roadmap, Use Case, và các phân tích nghiệp vụ.
