from __future__ import annotations

import time

from .parser import merge_filters, parse_query
from .providers import EmbeddingProvider, ResponseGenerator
from .repo import ChatRepository
from .schemas import ChatAskRequest, ChatAskResponse, ChatListing, ChatSource


class ChatService:
    """Stateless orchestration: parse, hybrid retrieve, rerank, answer."""

    def __init__(
        self,
        repo: ChatRepository,
        embedder: EmbeddingProvider,
        generator: ResponseGenerator,
        confidence_threshold: float = 0.65,
        max_results: int = 5,
    ):
        self.repo = repo
        self.embedder = embedder
        self.generator = generator
        self.confidence_threshold = confidence_threshold
        self.max_results = min(max_results, 5)

    def ask(self, body: ChatAskRequest) -> ChatAskResponse:
        started = time.perf_counter()
        parsed = parse_query(body.message)
        filters = merge_filters(parsed.filters, body.filters)

        degraded_reasons: list[str] = []
        listings: list[dict] = []
        if parsed.intent == "out_of_scope":
            answer = "Mình chỉ hỗ trợ tìm và so sánh nhà trọ quanh Đại học Cần Thơ."
            confidence = 0.0
            generation_provider = "rule"
            generation_model = None
        elif parsed.intent == "clarify":
            answer = "Bạn muốn tìm phòng ở khu vực nào, khoảng giá bao nhiêu và cần tiện ích gì?"
            confidence = 0.0
            generation_provider = "rule"
            generation_model = None
        else:
            embedded = self.embedder.embed_query(body.message)
            if embedded.degraded_reason:
                degraded_reasons.append(embedded.degraded_reason)
            listings = self.repo.retrieve(
                body.message, filters, embedded.vector, limit=self.max_results
            )
            filter_count = sum(
                value not in (None, [], "phong_tro") for value in filters.model_dump().values()
            )
            top_score = listings[0]["similarity_score"] if listings else 0.0
            confidence = min(0.97, 0.64 + 0.035 * filter_count + 0.22 * top_score) if listings else 0.0
            if confidence < self.confidence_threshold:
                listings = []
            generated = self.generator.generate(body.message, listings)
            answer = generated.text
            generation_provider = generated.provider
            generation_model = generated.model
            degraded_reasons.extend(generated.degraded_reasons)

        latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        listing_models = [
            ChatListing(
                id=item["id"],
                title=item["title"],
                price=item.get("price"),
                area=item.get("area"),
                address=item.get("address"),
                district=item.get("district"),
                amenities=item.get("parsed_amenities") or {},
                distance_to_ctu=item.get("distance_to_ctu"),
                route_time_campus=item.get("route_time_campus"),
                source=item["source"],
                source_url=item.get("source_url"),
                similarity_score=item["similarity_score"],
                vector_score=float(item.get("vector_score") or 0.0),
                bm25_score=float(item.get("bm25_score") or 0.0),
                rank=item["rank"],
                match_reasons=item.get("match_reasons") or [],
            )
            for item in listings
        ]
        sources = [
            ChatSource(
                listing_id=item.id,
                rank=item.rank,
                similarity_score=item.similarity_score,
                title=item.title,
                source=item.source,
                source_url=item.source_url,
            )
            for item in listing_models
        ]
        return ChatAskResponse(
            answer=answer,
            intent=parsed.intent,
            confidence=round(confidence, 4),
            listings=listing_models,
            sources=sources,
            no_answer=not listings,
            degraded=bool(degraded_reasons),
            degraded_reasons=degraded_reasons,
            generation_provider=generation_provider,
            generation_model=generation_model,
            latency_ms=latency_ms,
        )
