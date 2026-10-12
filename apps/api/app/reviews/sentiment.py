"""Small, deterministic Vietnamese sentiment model for review moderation.

The model is a multinomial Naive Bayes classifier trained in-process from a
curated seed corpus. It needs no network call or heavyweight runtime, making
the moderation path available in every deployment. The stored model version
keeps predictions auditable when the corpus or threshold changes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re
import unicodedata


MODEL_VERSION = "vi-review-nb-v1"
NEGATIVE_FLAG_THRESHOLD = 0.62


_TRAINING_DATA: tuple[tuple[str, str], ...] = (
    ("phòng sạch sẽ thoáng mát chủ nhà thân thiện", "positive"),
    ("giá hợp lý đúng như mô tả", "positive"),
    ("ở rất ổn an ninh tốt", "positive"),
    ("chủ nhà nhiệt tình hỗ trợ nhanh", "positive"),
    ("phòng đẹp tiện nghi đầy đủ", "positive"),
    ("vị trí thuận tiện gần trường", "positive"),
    ("khu trọ yên tĩnh và sạch", "positive"),
    ("điện nước rõ ràng không phát sinh", "positive"),
    ("hình ảnh đúng thực tế", "positive"),
    ("mình rất hài lòng sẽ giới thiệu bạn bè", "positive"),
    ("wifi mạnh chỗ để xe rộng", "positive"),
    ("phòng mới thoáng và đáng tiền", "positive"),
    ("chủ trọ dễ thương không làm khó", "positive"),
    ("mọi thứ tốt hơn mong đợi", "positive"),
    ("đã ở lâu và không có vấn đề", "positive"),
    ("phòng bẩn hôi và rất ẩm mốc", "negative"),
    ("chủ nhà thu phí vô lý", "negative"),
    ("giá thực tế cao hơn tin đăng", "negative"),
    ("hình ảnh giả phòng không giống mô tả", "negative"),
    ("nghi lừa đảo bắt chuyển cọc trước", "negative"),
    ("mất cọc chủ trọ không trả tiền", "negative"),
    ("an ninh kém thường xuyên mất đồ", "negative"),
    ("ồn ào cả đêm không ngủ được", "negative"),
    ("điện nước chặt chém quá đắt", "negative"),
    ("thái độ tệ khó chịu và thiếu tôn trọng", "negative"),
    ("phòng xuống cấp dột nước nguy hiểm", "negative"),
    ("nhà vệ sinh bẩn kinh khủng", "negative"),
    ("wifi yếu hay mất nước", "negative"),
    ("quảng cáo sai sự thật", "negative"),
    ("trải nghiệm rất tệ không nên thuê", "negative"),
    ("phòng bình thường đúng thông tin", "positive"),
    ("không tệ chủ nhà khá ổn", "positive"),
    ("giá rẻ nhưng phòng vẫn sạch", "positive"),
    ("không sạch sẽ và chủ trọ không hỗ trợ", "negative"),
    ("không an toàn không nên đặt cọc", "negative"),
    ("tạm ổn nhưng hơi xa trường", "positive"),
)

_TOKEN_PATTERN = re.compile(r"[0-9a-zA-ZÀ-ỹĐđ]+", re.UNICODE)


def _features(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    words = _TOKEN_PATTERN.findall(normalized)
    bigrams = [f"{left}_{right}" for left, right in zip(words, words[1:])]
    return words + bigrams


@dataclass(frozen=True)
class SentimentPrediction:
    label: str
    negative_score: float
    is_flagged: bool
    model_version: str = MODEL_VERSION


class VietnameseReviewSentimentModel:
    """Binary Naive Bayes with a neutral confidence band."""

    def __init__(self, training_data: tuple[tuple[str, str], ...] = _TRAINING_DATA):
        self.class_docs = Counter(label for _, label in training_data)
        self.token_counts = {"positive": Counter(), "negative": Counter()}
        self.total_tokens = Counter()
        self.vocabulary: set[str] = set()
        for text, label in training_data:
            tokens = _features(text)
            self.token_counts[label].update(tokens)
            self.total_tokens[label] += len(tokens)
            self.vocabulary.update(tokens)
        self.total_docs = len(training_data)

    def _log_probability(self, tokens: list[str], label: str) -> float:
        log_probability = math.log(self.class_docs[label] / self.total_docs)
        denominator = self.total_tokens[label] + len(self.vocabulary)
        counts = Counter(tokens)
        for token, frequency in counts.items():
            token_probability = (self.token_counts[label][token] + 1) / denominator
            log_probability += frequency * math.log(token_probability)
        return log_probability

    def predict(self, comment: str) -> SentimentPrediction:
        tokens = _features(comment)
        positive_log = self._log_probability(tokens, "positive")
        negative_log = self._log_probability(tokens, "negative")
        log_odds = max(-60.0, min(60.0, positive_log - negative_log))
        negative_score = 1.0 / (1.0 + math.exp(log_odds))

        if negative_score >= NEGATIVE_FLAG_THRESHOLD:
            label = "negative"
        elif negative_score <= 1.0 - NEGATIVE_FLAG_THRESHOLD:
            label = "positive"
        else:
            label = "neutral"
        return SentimentPrediction(
            label=label,
            negative_score=round(negative_score, 4),
            is_flagged=label == "negative",
        )


sentiment_model = VietnameseReviewSentimentModel()
