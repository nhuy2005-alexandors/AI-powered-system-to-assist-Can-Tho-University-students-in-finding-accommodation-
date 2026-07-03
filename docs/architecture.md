# System Architecture — Trọ CTU

## 1. Kiến trúc Tổng thể (High-level Architecture)

Hệ thống tuân theo kiến trúc Client-Server với các module AI và Crawler chạy bất đồng bộ.

```mermaid
graph TD
    subgraph "Client Tier"
        Guest[Guest User]
        Student[Student User]
        Admin[Admin]
    end

    subgraph "Frontend Tier (apps/web)"
        NextJS[Next.js App Router]
        Zustand[State Management]
        Tailwind[Tailwind CSS + shadcn/ui]
        
        NextJS --> Zustand
        NextJS --> Tailwind
    end

    subgraph "API Gateway & Load Balancing"
        Nginx[Nginx Reverse Proxy / Ingress]
    end

    subgraph "Backend Tier (apps/api)"
        FastAPI[FastAPI Server]
        AuthMod[Auth & Security]
        ListingMod[Listings CRUD]
        SearchMod[Search & Filter]
        ChatMod[Chatbot RAG]
        MatchMod[Roommate Matching]
        RecMod[Recommendation Engine]
        RiskMod[Risk Detection]
        
        FastAPI --> AuthMod
        FastAPI --> ListingMod
        FastAPI --> SearchMod
        FastAPI --> ChatMod
        FastAPI --> MatchMod
        FastAPI --> RecMod
        FastAPI --> RiskMod
    end

    subgraph "Background Workers"
        Crawler[Crawler Pipeline - APScheduler]
        Embedding[Embedding Service]
        
        Crawler --> Embedding
    end

    subgraph "Data & Infra Tier (infra/db)"
        PG[(PostgreSQL 16)]
        PostGIS[PostGIS Extension]
        PGVector[pgvector Extension]
        Redis[(Redis Cache)]
        Gemini[Google Gemini API]
        
        PG --- PostGIS
        PG --- PGVector
    end

    Guest --> NextJS
    Student --> NextJS
    Admin --> NextJS

    NextJS --> Nginx
    Nginx --> FastAPI

    AuthMod --> PG
    ListingMod --> PG
    SearchMod --> PG
    SearchMod --> PostGIS
    ChatMod --> PGVector
    ChatMod --> Gemini
    MatchMod --> PGVector
    RecMod --> PGVector
    RiskMod --> PG
    
    FastAPI --> Redis

    Crawler --> PG
```

## 2. Luồng Dữ liệu Crawler & AI Pipeline

```mermaid
flowchart LR
    subgraph "External Sources"
        PhongTro123[phongtro123.com]
        TroMoi[tromoi.com]
        Mogi[mogi.vn]
        BDS123[bds123.vn]
    end

    subgraph "Crawler Pipeline (Python)"
        Scraper[HTML Scraper]
        Normalizer[Data Normalizer]
        Dedup[Deduplication MinHash/SHA-256]
        Geocoding[Nominatim Geocoding]
    end

    subgraph "AI Services"
        Risk[Risk Scoring]
        Embedder[Text Embedding 384-dim]
    end

    subgraph "Database"
        DB[(PostgreSQL + PostGIS + pgvector)]
    end

    PhongTro123 --> Scraper
    TroMoi --> Scraper
    Mogi --> Scraper
    BDS123 --> Scraper

    Scraper --> Normalizer
    Normalizer --> Dedup
    Dedup --> Geocoding
    Geocoding --> Risk
    Geocoding --> Embedder
    
    Risk --> DB
    Embedder --> DB
```

## 3. Deployment Topology (Docker Compose)

```mermaid
graph TD
    subgraph "Docker Host (Local/VPS)"
        subgraph "Network: app-network"
            WEB[Web Container<br/>Node.js: Next.js<br/>Port: 3000]
            
            API[API Container<br/>Python: FastAPI + APScheduler<br/>Port: 8000]
            
            DB[(DB Container<br/>PostgreSQL 16 + PostGIS + pgvector<br/>Port: 5432)]
            
            CACHE[(Cache Container<br/>Redis<br/>Port: 6379)]
        end
    end

    WEB -- "HTTP/REST" --> API
    API -- "SQL/TCP" --> DB
    API -- "TCP" --> CACHE
```

> Hệ thống được đóng gói 100% bằng Docker. Frontend (`apps/web`) gọi Backend (`apps/api`) thông qua mạng nội bộ Docker hoặc qua exposed ports. Crawler chạy dưới dạng background thread (APScheduler) bên trong API Container để tiết kiệm tài nguyên (nguyên tắc P1).
