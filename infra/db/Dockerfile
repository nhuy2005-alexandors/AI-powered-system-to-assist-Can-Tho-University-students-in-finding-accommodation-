# PostGIS + pgvector in one image.
# pgvector ships a postgis-enabled variant; build extensions from the official combo.
FROM postgis/postgis:16-3.4

# install pgvector against the bundled PG16
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

# init scripts run once on first cluster init (empty data dir), in filename order
COPY init.sql /docker-entrypoint-initdb.d/10-init.sql
COPY migrations/20_listings.sql /docker-entrypoint-initdb.d/20-listings.sql
COPY migrations/30_users.sql /docker-entrypoint-initdb.d/30-users.sql
COPY migrations/40_auth.sql /docker-entrypoint-initdb.d/40-auth.sql
COPY migrations/50_route_time.sql /docker-entrypoint-initdb.d/50-route-time.sql
COPY migrations/50_ugc.sql /docker-entrypoint-initdb.d/50-ugc.sql
COPY migrations/60_data_cleaning.sql /docker-entrypoint-initdb.d/60-data-cleaning.sql
COPY migrations/70_listing_classify.sql /docker-entrypoint-initdb.d/70-listing-classify.sql
COPY migrations/90_chatbot.sql /docker-entrypoint-initdb.d/90-chatbot.sql
COPY migrations/91_room_service_risk.sql /docker-entrypoint-initdb.d/91-room-service-risk.sql
COPY migrations/92_reports_moderation.sql /docker-entrypoint-initdb.d/92-reports-moderation.sql
COPY migrations/93_ai_product_features.sql /docker-entrypoint-initdb.d/93-ai-product-features.sql
COPY migrations/94_legal_knowledge.sql /docker-entrypoint-initdb.d/94-legal-knowledge.sql
COPY migrations/95_fr_delivery.sql /docker-entrypoint-initdb.d/95-fr-delivery.sql
COPY migrations/96_reviews_sentiment.sql /docker-entrypoint-initdb.d/96-reviews-sentiment.sql
COPY migrations/97_response_performance.sql /docker-entrypoint-initdb.d/97-response-performance.sql
COPY migrations/98_legal_quality.sql /docker-entrypoint-initdb.d/98-legal-quality.sql
COPY migrations/99_chat_history.sql /docker-entrypoint-initdb.d/99-chat-history.sql
COPY migrations/100_shared_answers_document_control.sql /docker-entrypoint-initdb.d/100-shared-answers-document-control.sql
