"""Read-only E5/cosine recommendation demo for the handoff database."""
from __future__ import annotations

import argparse
import gc
import getpass
import math

import psycopg
from psycopg.rows import dict_row
from sentence_transformers import SentenceTransformer

from embed_handoff_listings import listing_text

MODEL = "intfloat/multilingual-e5-small"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"


def rerank(query: str, rows: list[dict]) -> list[dict]:
    """Score query/document pairs with a pretrained cross-encoder, no score mixing."""
    import torch
    from sentence_transformers import CrossEncoder

    print(f"Loading reranker: {RERANK_MODEL} (CPU; first run downloads model)")
    model = CrossEncoder(RERANK_MODEL, device="cpu", max_length=512)
    pairs = [(query, listing_text(row).removeprefix("passage: ")) for row in rows]
    truncated = sum(
        len(model.tokenizer(a, b, truncation=False)["input_ids"]) > 512
        for a, b in pairs
    )
    if truncated:
        print(f"Reranker: {truncated} query/document pairs exceed 512 tokens and will be truncated.")
    scores = model.predict(
        pairs, batch_size=2, show_progress_bar=True,
        activation_fct=torch.nn.Identity(),
    )
    if len(scores) != len(rows):
        raise RuntimeError("Reranker returned an unexpected number of scores")
    for row, score in zip(rows, scores):
        value = float(score)
        if not math.isfinite(value):
            raise RuntimeError("Reranker returned a nonfinite score")
        row["rerank_score"] = value
    return sorted(rows, key=lambda row: (-row["rerank_score"], row["cosine_rank"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--needs", default="Tôi tìm phòng trọ, ưu tiên có gác.")
    parser.add_argument("--max-price", type=int, default=2_000_000)
    parser.add_argument("--district", default="Quận Ninh Kiều",
                        help="Exact district name; pass an empty string for all districts")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--rerank", action="store_true", help="Rerank cosine candidates with local BGE")
    parser.add_argument("--candidate-k", type=int, default=50)
    args = parser.parse_args()
    if not args.needs.strip() or args.max_price <= 0 or not 1 <= args.top_k <= 100:
        parser.error("Needs must be nonempty, max-price positive, and top-k between 1 and 100")
    if args.rerank and not args.top_k <= args.candidate_k <= 1000:
        parser.error("candidate-k must be between top-k and 1000")

    query = f"query: {args.needs.strip()} Ngân sách tối đa {args.max_price} VND."
    if args.district:
        query += f" Khu vực: {args.district}."
    model = SentenceTransformer(MODEL, device="cpu")
    token_count = len(model.tokenizer(query, truncation=False)["input_ids"])
    if token_count > model.max_seq_length:
        parser.error("Needs text exceeds the model token limit; shorten it before embedding")
    vector = model.encode(query, normalize_embeddings=True)
    if len(vector) != 384 or not all(math.isfinite(float(v)) for v in vector):
        raise RuntimeError("Expected a finite 384-dimensional embedding")
    literal = "[" + ",".join(str(float(value)) for value in vector) + "]"
    del model
    gc.collect()

    password = getpass.getpass("Mat khau PostgreSQL handoff: ")
    with psycopg.connect(
        host="localhost", port=5454, dbname="nckh_handoff",
        user="nckh_handoff", password=password, row_factory=dict_row,
    ) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        filters = ["l.status = 'active'", "l.price > 0", "l.price <= %s",
                   "l.embedding_vector IS NOT NULL", "l.embedding_model = %s"]
        params: list = [args.max_price, MODEL]
        if args.district:
            filters.append("l.district = %s")
            params.append(args.district)
        # Materialize candidates so this demo scores all eligible rooms exactly,
        # even if an approximate vector index is added to the database later.
        sql = """
            WITH candidates AS MATERIALIZED (
                SELECT l.id, l.title, l.price, l.area, l.district,
                       l.description, l.address, l.parsed_amenities,
                       l.source_url, l.embedding_vector,
                       c.housing_type, c.offer_kind, c.description_state
                FROM public.aggregated_listings l
                JOIN public.catalog_handoff_v1 c ON c.id = l.id
                WHERE """ + " AND ".join(filters) + """
            )
            SELECT id, title, price, area, district, description, address,
                   parsed_amenities, source_url, housing_type, offer_kind, description_state,
                   1 - (embedding_vector <=> %s::vector) AS similarity,
                   count(*) OVER () AS candidate_count
            FROM candidates
            ORDER BY similarity DESC, id ASC
            LIMIT %s
        """
        retrieve_k = args.candidate_k if args.rerank else args.top_k
        rows = conn.execute(sql, [*params, literal, retrieve_k]).fetchall()

    print(f"Nhu cau: {args.needs}")
    print(f"Dieu kien: gia <= {args.max_price:,} VND; khu vuc = {args.district or 'tat ca'}")
    if not rows:
        print("Khong co tin phu hop co embedding E5. Thu doi ngan sach/khu vuc.")
        return
    print(f"Candidates={rows[0]['candidate_count']}; cosine_retrieved={len(rows)}")
    for rank, row in enumerate(rows, 1):
        row["cosine_rank"] = rank
    if args.rerank:
        print("Cosine top IDs: " + ", ".join(str(row["id"]) for row in rows[:args.top_k]))
        # Budget is already enforced by SQL. Do not repeat its numeric boundary
        # in the reranking query: relevance models can favor exact price matches
        # instead of distinguishing preferred amenities.
        rerank_query = args.needs.strip()
        if args.district:
            rerank_query += f" Khu vực: {args.district}."
        print(f"Rerank query: {rerank_query}")
        rows = rerank(rerank_query, rows)
        print("Rerank scores are raw model scores, not probabilities; higher ranks first.")
    rows = rows[:args.top_k]
    print(f"Returned={len(rows)}")
    print("Cosine la do tuong dong, khong phai xac suat hai long. Du lieu chua xac minh con phong.")
    for rank, row in enumerate(rows, 1):
        area = f"{row['area']:g} m2" if row["area"] is not None else "chua biet"
        print(f"\n{rank}. [ID {row['id']}] {row['title']}")
        print(f"   Gia nguon: {row['price']:,} VND | Dien tich: {area}")
        print(f"   Loai: {row['housing_type']} | Hinh thuc: {row['offer_kind']} | Cosine: {row['similarity']:.4f}")
        if args.rerank:
            print(f"   Hang cosine cu: {row['cosine_rank']} | Rerank: {row['rerank_score']:.4f}")
        description = " ".join((row["description"] or "").split())
        if description:
            print(f"   Mo ta (trich): {description[:350]}")
        print(f"   Nguon: {row['source_url']}")


if __name__ == "__main__":
    main()
