"""Build a bounded preference vector from implicit feedback.

Weights are heuristics. Each listing contributes its strongest eligible action.
"""
import math

VECTOR_DIMENSIONS = 384
EVENT_WEIGHTS = {"view": 1.0, "save": 3.0, "contact": 5.0}
MIN_VIEW_DURATION_MS = 5_000
MAX_BEHAVIOR_BLEND = 0.35


def normalize_vector(value) -> list[float]:
    if isinstance(value, (str, bytes, dict)):
        raise ValueError("Expected a numeric vector")
    try:
        values = [float(component) for component in value]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Expected a numeric vector") from exc
    if len(values) != VECTOR_DIMENSIONS or not all(math.isfinite(v) for v in values):
        raise ValueError("Expected 384 finite components")
    norm = math.hypot(*values)
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError("Expected a nonzero vector")
    return [v / norm for v in values]


def build_behavior_profile(initial_vector, signals, embeddings, excluded=()) -> dict:
    initial = normalize_vector(initial_vector)
    blocked = set(excluded)
    blocked.update(
        event["listing_id"]
        for event in signals
        if event.get("type") == "not_interested"
    )
    weights = {}
    for event in signals:
        listing_id = event.get("listing_id")
        kind = event.get("type")
        if listing_id in blocked or kind not in EVENT_WEIGHTS:
            continue
        if kind == "view":
            duration = event.get("duration_ms")
            if (
                not isinstance(duration, (int, float))
                or not math.isfinite(duration)
                or duration < MIN_VIEW_DURATION_MS
            ):
                continue
        weights[listing_id] = max(weights.get(listing_id, 0.0), EVENT_WEIGHTS[kind])

    learned = []
    for listing_id, weight in sorted(weights.items()):
        try:
            vector = normalize_vector(embeddings.get(listing_id))
        except ValueError:
            continue
        learned.append((listing_id, vector, weight))

    total_weight = sum(weight for _, _, weight in learned)
    blend = min(MAX_BEHAVIOR_BLEND, total_weight / 20.0)
    vector = initial
    if learned:
        centroid = [
            math.fsum(room[index] * weight for _, room, weight in learned) / total_weight
            for index in range(VECTOR_DIMENSIONS)
        ]
        try:
            centroid = normalize_vector(centroid)
        except ValueError:
            # Opposing vectors can cancel, leaving no useful direction.
            blend = 0.0
        if blend:
            vector = normalize_vector(
                [
                    (1.0 - blend) * declared + blend * observed
                    for declared, observed in zip(initial, centroid)
                ]
            )
    return {
        "preference_vector": vector,
        "behavior_listing_count": len(learned),
        "behavior_weight": total_weight,
        "behavior_blend": blend,
        "behavior_signal_weights": {
            str(listing_id): weight for listing_id, _, weight in learned
        },
    }
