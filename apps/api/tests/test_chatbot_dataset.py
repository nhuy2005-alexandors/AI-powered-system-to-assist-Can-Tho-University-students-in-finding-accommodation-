import importlib.util
import json
import os
from pathlib import Path


ROOT = (
    Path(os.environ["PROJECT_ROOT"])
    if "PROJECT_ROOT" in os.environ
    else Path(__file__).resolve().parents[3]
)
GENERATOR_PATH = ROOT / "scripts/generate_fake_listings.py"
spec = importlib.util.spec_from_file_location("generate_fake_listings", GENERATOR_PATH)
generator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(generator)


def test_generator_is_deterministic_and_has_required_distribution():
    first = [generator.listing_record(i, __import__("random").Random(2026 + i)) for i in range(1000)]
    second = [generator.listing_record(i, __import__("random").Random(2026 + i)) for i in range(1000)]
    assert first == second
    assert sum(item["status"] == "active" for item in first) == 800
    assert sum(item["status"] == "expired" for item in first) == 100
    assert sum(item["status"] == "flagged" for item in first) == 50
    assert sum(item["status"] == "hidden" for item in first) == 50
    assert sum(item["cleaning"] == "cleaned" for item in first) == 850
    assert sum(item["cleaning"] == "raw" for item in first) == 100
    assert sum(item["cleaning"] == "rejected" for item in first) == 50
    assert sum(item["listing_type"] == "phong_tro" for item in first) == 750
    assert sum(item["listing_type"] == "nha_nguyen_can" for item in first) == 100
    assert sum(item["listing_type"] == "mat_bang" for item in first) == 80
    assert sum(item["listing_type"] == "khac" for item in first) == 70


def test_eval_dataset_has_exact_categories_and_fields():
    path = ROOT / "eval/datasets/chatbot_eval.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 200
    assert sum(case["id"].startswith("answer-") for case in cases) == 120
    assert sum(case["id"].startswith("no-answer-") for case in cases) == 30
    assert sum(case["id"].startswith("out-of-scope-") for case in cases) == 20
    assert sum(case["id"].startswith("stateless-") for case in cases) == 30
    assert all(case["conversation_history"] == [] for case in cases)
    required = {
        "id",
        "question",
        "conversation_history",
        "expected_listing_ids",
        "expected_filters",
        "expected_intent",
        "should_answer",
        "forbidden_listing_ids",
        "notes",
        "tags",
    }
    assert all(required <= set(case) for case in cases)


def test_seed_sql_contains_no_random_embedding_vectors():
    seed = (ROOT / "infra/db/seeds/dev_chatbot.sql").read_text(encoding="utf-8")
    assert "embedding_vector=NULL" in seed
    assert "VECTOR(" not in seed
    assert "random()" not in seed.lower()
    assert "chat_sessions" not in seed
    assert "chat_messages" not in seed
