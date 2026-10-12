"""PHUC RAGAS framework adapted to authenticated /chatbot/ask on feature.

Collection and scoring are separate checkpoints. No reference answer is invented.
Metric coverage and errors are retained instead of replacing failures with zero.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
from datetime import datetime, timezone

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
METRICS = ("faithfulness", "answer_relevancy", "context_utilization")


def load_cases(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Dataset cần có id duy nhất và ít nhất một câu hỏi")
    if any(not isinstance(row.get("question"), str) or not row["question"].strip() for row in rows):
        raise ValueError("Mỗi mẫu cần có question")
    return rows


def source_hash() -> str:
    digest = hashlib.sha256()
    paths = sorted((ROOT / "apps/api/app/room_service").rglob("*.py"))
    paths += [Path(__file__), ROOT / "eval/ollama_judge.py", ROOT / "eval/requirements-ragas.txt"]
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).replace("\\", "/").encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def summarize(report: dict) -> dict:
    cases = report["cases"]
    completed = [case for case in cases if "answer" in case and "error" not in case]
    latencies = sorted(case["latency_ms"] for case in cases if "latency_ms" in case)
    citations = [case["citation_format_accuracy"] for case in completed
                 if case.get("citation_applicable") and case.get("sources")]
    summary = {
        "questions": len(cases), "completed": len(completed),
        "errors": sum("error" in case for case in cases),
        "error_rate": sum("error" in case for case in cases) / len(cases) if cases else None,
        "partial_answer": sum(bool(case.get("partial_answer")) for case in completed),
        "partial_answer_rate": sum(bool(case.get("partial_answer")) for case in completed) / len(completed) if completed else None,
        "no_answer": sum(bool(case.get("no_answer")) for case in completed),
        "degraded": sum(bool(case.get("degraded")) for case in completed),
        "latency_p50_ms": statistics.median(latencies) if latencies else None,
        "latency_p95_ms": latencies[math.ceil(.95 * len(latencies)) - 1] if latencies else None,
        "citation_format_accuracy_mean": statistics.mean(citations) if citations else None,
        "citation_scored": len(citations),
        "ragas": {},
        "reference_metrics": "N/A: fixture questions have no independent reference answers",
        "citation_scope": "Bracket/rank consistency only; source support is evaluated separately by faithfulness",
    }
    for name in METRICS:
        values = [case.get("ragas", {}).get(name) for case in completed]
        valid = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
        summary["ragas"][name] = {
            "mean": statistics.mean(valid) if valid else None,
            "scored": len(valid),
            "errors": sum(name in case.get("ragas_errors", {}) for case in completed),
        }
    report["summary"] = summary
    return summary


def save_report(path: Path, report: dict) -> None:
    summarize(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def collect(client: httpx.Client, cases: list[dict], report: dict, output: Path) -> None:
    from app.room_service.chatbot.service import _citation_accuracy

    manifest = client.get("/admin/documents/evaluation-manifest")
    manifest.raise_for_status()
    current = manifest.json()
    if report.get("server_manifest") not in (None, current):
        raise ValueError("Model/corpus đã thay đổi; hãy dùng file output mới")
    report["server_manifest"] = current
    for index, case in enumerate(cases):
        previous = report["cases"][index]
        if "answer" in previous and "error" not in previous:
            continue
        row = dict(case)
        started = time.perf_counter()
        try:
            response = client.post("/chatbot/ask", json={
                "message": case["question"],
                "conversation_history": case.get("conversation_history", []),
                "include_evaluation_contexts": True,
            })
            # Authentication and throttling require a new token or a later resume.
            if response.status_code in (401, 403, 429):
                response.raise_for_status()
            response.raise_for_status()
            data = response.json()
            row.update({key: data.get(key) for key in (
                "answer", "sources", "listings", "partial_answer", "no_answer", "degraded",
                "degraded_reasons", "retrieval_mode", "generation_provider", "generation_model",
                "corpus_schema", "citation_applicable", "event_id",
            )})
            if not isinstance(row["answer"], str):
                raise ValueError("API response thiếu answer")
            row["contexts"] = data.get("evaluation_contexts") or []
            row["citation_format_accuracy"] = _citation_accuracy(row["answer"], row.get("sources") or [])
            row["server_latency_ms"] = data.get("latency_ms")
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"[:500]
            row.pop("answer", None)
            row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            report["cases"][index] = row
            save_report(output, report)
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (401, 403, 429):
                raise
            continue
        row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        report["cases"][index] = row
        save_report(output, report)
    ending = client.get("/admin/documents/evaluation-manifest")
    ending.raise_for_status()
    report["corpus_changed_during_collection"] = current != ending.json()
    save_report(output, report)
    if report["corpus_changed_during_collection"]:
        raise ValueError("Model/corpus thay đổi trong lúc chạy; kết quả không so sánh trực tiếp được")


def score(report: dict, output: Path, judge_url: str, judge_model: str, embedding_model: str) -> None:
    # Our own content hashes provide versioning; a git binary is optional here.
    os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")
    import ragas
    from ragas.embeddings.base import BaseRagasEmbedding
    from ragas.metrics.collections import AnswerRelevancy, ContextUtilization, Faithfulness
    from app.room_service.chatbot.providers import E5EmbeddingProvider
    from ollama_judge import OllamaRagasLLM

    class Embeddings(BaseRagasEmbedding):
        def __init__(self):
            super().__init__()
            self.provider = E5EmbeddingProvider(embedding_model)

        def embed_text(self, text, **kwargs):
            result = self.provider.embed_query(text)
            if result.vector is None:
                raise RuntimeError(result.degraded_reason or "Embedding unavailable")
            return result.vector

        async def aembed_text(self, text, **kwargs):
            return await asyncio.to_thread(self.embed_text, text, **kwargs)

    judge_meta = {"ragas_version": ragas.__version__, "provider": "ollama", "model": judge_model,
                  "url": judge_url, "embedding_model": embedding_model}
    if report.get("judge") not in (None, judge_meta):
        raise ValueError("Judge đã thay đổi; hãy dùng output mới để tránh trộn điểm")
    report["judge"] = judge_meta
    judge = OllamaRagasLLM(judge_url, judge_model, max_output_tokens=4096, timeout_seconds=300)
    metrics = {"faithfulness": Faithfulness(llm=judge),
               "answer_relevancy": AnswerRelevancy(llm=judge, embeddings=Embeddings(), strictness=1),
               "context_utilization": ContextUtilization(llm=judge)}
    for case in report["cases"]:
        if "answer" not in case or "error" in case or case.get("no_answer") or not case.get("contexts"):
            case["ragas_skipped"] = "No successful grounded answer"
            continue
        for name, metric in metrics.items():
            if name in case.get("ragas", {}):
                continue
            kwargs = {"user_input": case["question"], "response": case["answer"]}
            if name != "answer_relevancy":
                kwargs["retrieved_contexts"] = [item["content"] for item in case["contexts"]]
            usage_start = len(judge.usage)
            try:
                value = float(metric.score(**kwargs).value)
                if not math.isfinite(value):
                    raise ValueError("Non-finite RAGAS score")
                case.setdefault("ragas", {})[name] = round(value, 4)
                case.setdefault("ragas_errors", {}).pop(name, None)
            except Exception as exc:
                case.setdefault("ragas_errors", {})[name] = f"{type(exc).__name__}: {exc}"[:500]
            case.setdefault("ragas_usage", {})[name] = judge.usage[usage_start:]
            save_report(output, report)
    save_report(output, report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    parser.add_argument("--admin-token", default=os.getenv("ADMIN_ACCESS_TOKEN"))
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval/datasets/chatbot_smoke.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/feature_ragas.json")
    parser.add_argument("--phase", choices=("collect", "score", "all"), default="collect")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--judge-url", default=os.getenv("RAGAS_JUDGE_URL", "http://localhost:11434"))
    parser.add_argument("--judge-model", default=os.getenv("RAGAS_JUDGE_MODEL"))
    parser.add_argument("--embedding-model", default="intfloat/multilingual-e5-small")
    parser.add_argument("--prompt-version", default="feature-chatbot-v1")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.phase in ("collect", "all") and not args.admin_token:
        parser.error("Cần ADMIN_ACCESS_TOKEN của admin để lấy evaluation_contexts")
    if args.phase in ("score", "all") and not args.judge_model:
        parser.error("Cần --judge-model hoặc RAGAS_JUDGE_MODEL; bước score sẽ gọi model chấm")
    if args.output.exists():
        report = json.loads(args.output.read_text(encoding="utf-8"))
    elif args.phase == "score":
        parser.error("Chưa có checkpoint collect")
    else:
        report = {}
    if args.phase in ("collect", "all"):
        cases = load_cases(args.dataset)
        if args.limit:
            cases = cases[:args.limit]
        metadata = {
            "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
            "dataset_version": cases[0].get("dataset_version", "unknown"),
            "pipeline_sha256": source_hash(), "prompt_version": args.prompt_version,
            "api_url": args.api_url, "case_ids": [case["id"] for case in cases],
        }
        if report.get("metadata") not in (None, metadata):
            parser.error("Dataset/code/config khác checkpoint; hãy chọn output mới")
        report.setdefault("created_at_utc", datetime.now(timezone.utc).isoformat())
        report["metadata"] = metadata
        report.setdefault("cases", cases)
        with httpx.Client(base_url=args.api_url, headers={"Authorization": f"Bearer {args.admin_token}"}, timeout=300) as client:
            collect(client, cases, report, args.output)
    if args.phase in ("score", "all"):
        if report.get("corpus_changed_during_collection"):
            parser.error("Không chấm checkpoint có corpus thay đổi trong lúc collect")
        score(report, args.output, args.judge_url, args.judge_model, args.embedding_model)
    print(json.dumps(summarize(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
