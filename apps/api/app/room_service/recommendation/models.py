"""Lazy local model loading; one inference call at a time per worker."""
import json
import math
from threading import Lock

from fastapi import HTTPException

from .behavior import VECTOR_DIMENSIONS

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_CANDIDATE_COUNT = 20
RERANK_MAX_LENGTH = 384
RERANK_BATCH_SIZE = 4


def room_text(row: dict) -> str:
    fields = [
        ("Tiêu đề", row.get("title")),
        ("Loại nhà", row.get("housing_type")),
        ("Loại chào thuê", row.get("offer_kind")),
        ("Giá nguồn (VND, kỳ giá chưa xác minh)", row.get("price")),
        ("Diện tích (m²)", row.get("area")),
        ("Địa chỉ", row.get("address")),
        ("Quận/huyện", row.get("district")),
        ("Mô tả", row.get("description")),
        ("Trạng thái mô tả", row.get("description_state")),
    ]
    result = "\n".join(
        f"{key}: {value}" for key, value in fields if value is not None and value != ""
    )
    if row.get("parsed_amenities"):
        result += "\nTiện ích được nêu: " + json.dumps(
            row["parsed_amenities"], ensure_ascii=False, sort_keys=True
        )
    return result


class LocalModels:
    def __init__(self):
        self.encoder = None
        self.reranker = None
        self.lock = Lock()

    def embed(self, preferences) -> list[float]:
        query = f"query: {preferences.needs} Ngân sách tối đa {preferences.max_price} VND."
        if preferences.district:
            query += f" Khu vực: {preferences.district}."
        with self.lock:
            try:
                from sentence_transformers import SentenceTransformer

                if self.encoder is None:
                    self.encoder = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
                token_count = len(
                    self.encoder.tokenizer(query, truncation=False)["input_ids"]
                )
                if token_count > self.encoder.max_seq_length:
                    raise HTTPException(422, "Nhu cầu quá dài; hãy rút ngắn nội dung")
                vector = [
                    float(v)
                    for v in self.encoder.encode(query, normalize_embeddings=True)
                ]
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    503, "Không chạy được E5; kiểm tra môi trường ML và model local"
                ) from None
        if len(vector) != VECTOR_DIMENSIONS or not all(math.isfinite(v) for v in vector):
            raise HTTPException(503, "E5 trả về vector không hợp lệ")
        return vector

    def rerank(self, preferences, rows: list[dict]) -> tuple[list[dict], int]:
        query = preferences.needs
        if preferences.district:
            query += f" Khu vực: {preferences.district}."
        with self.lock:
            try:
                import torch
                from sentence_transformers import CrossEncoder

                if self.reranker is None:
                    self.reranker = CrossEncoder(
                        RERANKER_MODEL, device="cpu", max_length=RERANK_MAX_LENGTH
                    )
                pairs = [(query, room_text(row)) for row in rows]
                truncated = sum(
                    len(self.reranker.tokenizer(a, b, truncation=False)["input_ids"])
                    > RERANK_MAX_LENGTH
                    for a, b in pairs
                )
                scores = self.reranker.predict(
                    pairs,
                    batch_size=RERANK_BATCH_SIZE,
                    activation_fct=torch.nn.Identity(),
                )
                if len(scores) != len(rows) or not all(
                    math.isfinite(float(score)) for score in scores
                ):
                    raise ValueError("Invalid rerank scores")
            except Exception:
                raise HTTPException(
                    503, "Không chạy được BGE reranker; thử rerank=false"
                ) from None
        for row, score in zip(rows, scores):
            row["rerank_score"] = float(score)
        ranked = sorted(rows, key=lambda row: (-row["rerank_score"], row["cosine_rank"]))
        return ranked, truncated
