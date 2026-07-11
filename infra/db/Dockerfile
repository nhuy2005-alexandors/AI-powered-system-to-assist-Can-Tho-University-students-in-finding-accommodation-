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
COPY migrations/50_ugc.sql /docker-entrypoint-initdb.d/50-ugc.sql
COPY migrations/60_data_cleaning.sql /docker-entrypoint-initdb.d/60-data-cleaning.sql
COPY migrations/70_listing_classify.sql /docker-entrypoint-initdb.d/70-listing-classify.sql
