"""Lazy local model loading; one inference call at a time per worker."""
import json
import math
from collections import OrderedDict
from hashlib import sha256
from threading import Lock
from time import monotonic

from fastapi import HTTPException

from .behavior import VECTOR_DIMENSIONS

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_CANDIDATE_COUNT = 50
RERANK_MAX_LENGTH = 512
RERANK_BATCH_SIZE = 2
RERANK_CACHE_SIZE = 1024
RERANK_CACHE_TTL_SECONDS = 300


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
        # Only model scores are cached. Eligibility and personalization are read afresh.
        self.rerank_cache = OrderedDict()

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
        if not rows:
            return [], 0
        query = preferences.needs
        if preferences.district:
            query += f" Khu vực: {preferences.district}."
        with self.lock:
            try:
                import torch
                from sentence_transformers import CrossEncoder

                pairs = [(query, room_text(row)) for row in rows]
                keys = [
                    sha256(json.dumps(
                        [RERANKER_MODEL, RERANK_MAX_LENGTH, a, b],
                        ensure_ascii=False,
                    ).encode("utf-8")).digest()
                    for a, b in pairs
                ]
                now = monotonic()
                for key in list(self.rerank_cache):
                    if self.rerank_cache[key][2] <= now:
                        del self.rerank_cache[key]
                values = {}
                missing = {}
                for key, pair in zip(keys, pairs):
                    if key in self.rerank_cache:
                        score, length, _ = self.rerank_cache[key]
                        values[key] = (score, length)
                        self.rerank_cache.move_to_end(key)
                    else:
                        missing[key] = pair
                if missing and self.reranker is None:
                    self.reranker = CrossEncoder(
                        RERANKER_MODEL, device="cpu", max_length=RERANK_MAX_LENGTH
                    )
                if missing:
                    lengths = {
                        key: len(self.reranker.tokenizer(a, b, truncation=False)["input_ids"])
                        for key, (a, b) in missing.items()
                    }
                    # Similar lengths reduce padding within each inference batch.
                    ordered = sorted(missing, key=lambda key: min(lengths[key], RERANK_MAX_LENGTH))
                    predicted = self.reranker.predict(
                        [missing[key] for key in ordered],
                        batch_size=RERANK_BATCH_SIZE,
                        activation_fct=torch.nn.Identity(),
                        show_progress_bar=False,
                    )
                    if len(predicted) != len(ordered) or not all(
                        math.isfinite(float(score)) for score in predicted
                    ):
                        raise ValueError("Invalid rerank scores")
                    expires = monotonic() + RERANK_CACHE_TTL_SECONDS
                    for key, score in zip(ordered, predicted):
                        values[key] = (float(score), lengths[key])
                        self.rerank_cache[key] = (float(score), lengths[key], expires)
                        self.rerank_cache.move_to_end(key)
                    while len(self.rerank_cache) > RERANK_CACHE_SIZE:
                        self.rerank_cache.popitem(last=False)
                scores = [values[key][0] for key in keys]
                truncated = sum(values[key][1] > RERANK_MAX_LENGTH for key in keys)
            except Exception:
                raise HTTPException(
                    503, "Không chạy được BGE reranker; thử rerank=false"
                ) from None
        for row, score in zip(rows, scores):
            row["rerank_score"] = float(score)
        ranked = sorted(rows, key=lambda row: (-row["rerank_score"], row["cosine_rank"]))
        return ranked, truncated
