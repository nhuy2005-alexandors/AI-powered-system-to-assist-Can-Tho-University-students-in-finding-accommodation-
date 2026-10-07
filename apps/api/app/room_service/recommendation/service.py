"""Recommendations using declared needs and bounded implicit feedback."""
import math
from time import perf_counter

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from .behavior import (
    EVENT_WEIGHTS,
    MIN_VIEW_DURATION_MS,
    VECTOR_DIMENSIONS,
    build_behavior_profile,
)
from .models import EMBEDDING_MODEL, RERANKER_MODEL, LocalModels
from .schemas import Preferences, RecommendationItem, RecommendationsOut


class RecommendationService:
    def __init__(self, listings, profiles):
        self.listings = listings
        self.profiles = profiles
        self.models = LocalModels()

    def recommend(self, preferences, top_k=10, rerank=False, vector=None, excluded=None):
        started = perf_counter()
        vector = vector if vector is not None else self.models.embed(preferences)
        if len(vector) != VECTOR_DIMENSIONS or not all(math.isfinite(v) for v in vector):
            raise HTTPException(409, "Vector hồ sơ không hợp lệ; cập nhật nhu cầu")
        try:
            rows = self.listings.search(
                vector,
                preferences,
                EMBEDDING_MODEL,
                max(50, top_k) if rerank else top_k,
                excluded or [],
            )
        except SQLAlchemyError:
            raise HTTPException(
                503, "Không truy vấn được phòng; kiểm tra PostgreSQL và migration embedding"
            ) from None
        count = int(rows[0]["eligible_count"]) if rows else 0
        retrieved = len(rows)
        for rank, row in enumerate(rows, 1):
            row["cosine_rank"] = rank
        warnings = [
            "Thông tin nguồn chưa xác minh còn phòng; giá nguồn chưa được kiểm chứng độc lập."
        ]
        if rows and rerank:
            rows, truncated = self.models.rerank(preferences, rows)
            if truncated:
                warnings.append(
                    f"Reranker cắt bớt nội dung của {truncated} cặp vượt 512 token."
                )
        if not rows:
            warnings.append("Không có phòng có embedding tương thích thỏa điều kiện đã chọn.")
        items = [
            RecommendationItem(
                listing_id=row["id"],
                **{
                    key: row.get(key)
                    for key in RecommendationItem.model_fields
                    if key != "listing_id"
                },
            )
            for row in rows[:top_k]
        ]
        return RecommendationsOut(
            preferences=preferences,
            items=items,
            eligible_count=count,
            retrieved_count=retrieved,
            embedding_model=EMBEDDING_MODEL,
            reranker_model=RERANKER_MODEL if rows and rerank else None,
            elapsed_ms=int((perf_counter() - started) * 1000),
            warnings=warnings,
        )

    def save_preferences(self, user_id, preferences):
        return self.profiles.save(
            user_id, preferences, self.models.embed(preferences), EMBEDDING_MODEL
        )

    def profile(self, user_id):
        return self.refresh_profile(user_id)[0]

    def refresh_profile(self, user_id):
        """Rebuild from stored events and retry concurrent profile changes.

        Rebuild from initial_vector so repeated reads do not compound learning.
        Stored events also repair an earlier failed profile update.
        """
        for _ in range(3):
            profile = self.profiles.get(user_id)
            if profile is None:
                raise HTTPException(404, "Bạn chưa lưu nhu cầu tìm phòng")
            if profile["embedding_model"] != EMBEDDING_MODEL:
                raise HTTPException(409, "Model hồ sơ đã đổi; hãy cập nhật nhu cầu")
            since = profile.get("behavior_since", profile.get("updated_at"))
            signals = self.profiles.recent_signals(
                user_id, since, profile.get("profile_generation")
            )
            excluded = self.profiles.excluded(user_id)
            listing_ids = sorted({event["listing_id"] for event in signals} - set(excluded))
            try:
                embeddings = self.listings.embeddings(listing_ids, EMBEDDING_MODEL)
            except SQLAlchemyError:
                raise HTTPException(
                    503, "Không đọc được vector phòng để cập nhật sở thích"
                ) from None
            try:
                changes = build_behavior_profile(
                    profile["initial_vector"], signals, embeddings, excluded
                )
            except (KeyError, ValueError):
                raise HTTPException(
                    409, "Vector nhu cầu ban đầu không hợp lệ; hãy cập nhật nhu cầu"
                ) from None
            changes["behavior_since"] = since
            try:
                same_vector = (
                    len(profile.get("preference_vector", []))
                    == len(changes["preference_vector"])
                    and all(
                        math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12)
                        for a, b in zip(
                            profile["preference_vector"], changes["preference_vector"]
                        )
                    )
                )
            except (TypeError, ValueError):
                same_vector = False
            if same_vector and all(
                profile.get(key) == value
                for key, value in changes.items()
                if key != "preference_vector"
            ):
                return profile, False
            updated = self.profiles.compare_and_update(user_id, profile, changes)
            if updated is not None:
                return updated, True
        raise HTTPException(409, "Hồ sơ vừa thay đổi đồng thời; hãy thử lại để cập nhật sở thích")

    def for_you(self, user_id, top_k, rerank):
        started = perf_counter()
        profile = self.profile(user_id)
        result = self.recommend(
            Preferences(**profile["preferences"]),
            top_k,
            rerank,
            profile["preference_vector"],
            self.profiles.excluded(user_id),
        )
        if rerank and profile.get("behavior_blend", 0) > 0:
            result.warnings.append(
                "Hành vi ảnh hưởng bước chọn ứng viên; reranker xếp lại theo nhu cầu đã nhập."
            )
        result.elapsed_ms = int((perf_counter() - started) * 1000)
        return result

    def record(self, user_id, event):
        try:
            exists = self.listings.exists(event.listing_id)
        except SQLAlchemyError:
            raise HTTPException(503, "Không kiểm tra được ID phòng trong PostgreSQL") from None
        if not exists:
            raise HTTPException(404, "Phòng không tồn tại")
        previous = self.profiles.get(user_id)
        generation = previous.get("profile_generation") if previous else None
        result = self.profiles.record(user_id, event, generation)
        try:
            profile, changed = self.refresh_profile(user_id)
        except HTTPException as exc:
            status = "no_profile" if exc.status_code == 404 else "pending"
            result.update(
                profile_updated=False,
                learning_status=status,
                event_learning_reason=status,
                learning_warning=exc.detail,
            )
            return result
        result.update(
            profile_updated=changed,
            learning_status="updated" if changed else "unchanged",
            event_learning_reason="pending",
            profile_version=profile["profile_version"],
            behavior_listing_count=profile.get("behavior_listing_count", 0),
        )
        try:
            excluded = (
                event.type == "not_interested"
                or event.listing_id in self.profiles.excluded(user_id)
            )
        except HTTPException as exc:
            # Keep the saved result if the lookup used to explain it fails.
            result["learning_warning"] = exc.detail
            return result
        if excluded:
            reason = "excluded"
        elif generation != profile.get("profile_generation"):
            reason = "stale_generation"
        elif event.type == "view" and (
            event.duration_ms is None or event.duration_ms < MIN_VIEW_DURATION_MS
        ):
            reason = "short_view"
        elif str(event.listing_id) not in profile.get("behavior_signal_weights", {}):
            reason = "unavailable_embedding"
        elif (previous or {}).get("behavior_signal_weights", {}).get(
            str(event.listing_id), 0
        ) >= EVENT_WEIGHTS[event.type]:
            reason = "duplicate_signal"
        else:
            reason = "eligible"
        result["event_learning_reason"] = reason
        return result
