"""Run the 58-question CTU corpus through the real retrieval/generation service and Ragas.

This runner is intentionally separate from the public API: evaluation contexts are
collected internally, and chatbot event recording is disabled. It never invents a
reference answer. Metrics that require independent references remain unreported.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, "/workspace/apps/api")
sys.path.insert(0, str(ROOT / "apps/api"))

QUESTION_RE = re.compile(r"^(\d+)\.\s+(.+)$")
CATEGORY_RE = re.compile(r"`([a-z_]+)`")
METRIC_NAMES = ("faithfulness", "answer_relevancy", "context_utilization")
from quota_checkpoint import QuotaCoordinator, QuotaPause, bounded_scoring, checkpoint_pause
QUOTA = QuotaCoordinator()


def load_questions(path: Path) -> list[dict]:
    category = "find_listing"
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            match = CATEGORY_RE.search(line)
            if match:
                category = match.group(1)
        match = QUESTION_RE.match(line)
        if match:
            cases.append({"id": int(match.group(1)), "question": match.group(2), "category": category})
    ids = [case["id"] for case in cases]
    if ids != list(range(1, len(ids) + 1)) or not ids:
        raise ValueError(f"Expected a consecutively numbered question bank, got {ids}")
    return cases


def save_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def summarize(report: dict) -> None:
    cases = report["cases"]
    completed = [case for case in cases if "answer" in case]
    metrics = {}
    for name in METRIC_NAMES:
        values = [case.get("ragas", {}).get(name) for case in completed]
        valid = [float(value) for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
        metrics[name] = {"mean": round(statistics.mean(valid), 4) if valid else None, "scored": len(valid)}
    latencies = [case["latency_ms"] for case in completed if isinstance(case.get("latency_ms"), (int, float))]
    citation = [case["citation_accuracy"] for case in completed if case.get("sources") and isinstance(case.get("citation_accuracy"), (int, float))]
    report["summary"] = {
        "questions": len(cases),
        "completed": len(completed),
        "errors": sum("error" in case for case in cases),
        "with_contexts": sum(bool(case.get("contexts")) for case in completed),
        "no_answer": sum(bool(case.get("no_answer")) for case in completed),
        "partial_answer": sum(bool(case.get("partial_answer")) for case in completed),
        "degraded": sum(bool(case.get("degraded")) for case in completed),
        "vector_retrieval": sum(case.get("retrieval_mode") in {"hybrid", "legal_hybrid", "graph_hybrid", "legal_graph_hybrid"} for case in completed),
        "category_source_match": sum(case.get("category_source_match") is True for case in completed),
        "category_source_evaluated": sum(case.get("category_source_match") is not None for case in completed),
        "citation_format_accuracy_mean": round(statistics.mean(citation), 4) if citation else None,
        "latency_p50_ms": round(statistics.median(latencies), 1) if latencies else None,
        "latency_p95_ms": round(sorted(latencies)[math.ceil(.95 * len(latencies)) - 1], 1) if latencies else None,
        "ragas": metrics,
        "context_recall": "N/A: no independent reference answers",
        "answer_correctness": "N/A: no independent reference answers",
    }
    by_category = {}
    for category in dict.fromkeys(case["category"] for case in cases):
        group = [case for case in completed if case["category"] == category]
        by_category[category] = {
            "questions": len([case for case in cases if case["category"] == category]),
            "completed": len(group),
            "with_contexts": sum(bool(case.get("contexts")) for case in group),
            "no_answer": sum(bool(case.get("no_answer")) for case in group),
        }
    report["by_category"] = by_category


def pipeline_sha256(pipeline: Path) -> str:
    files = sorted([*pipeline.glob('*.py'), *pipeline.parent.joinpath('legal_knowledge').glob('*.py')])
    return hashlib.sha256(b''.join(p.relative_to(pipeline.parent).as_posix().encode()+p.read_bytes() for p in files)).hexdigest()


def collect(report: dict, output: Path, limit: int | None, ids: list[int] | None = None) -> None:
    from sqlalchemy import create_engine
    from app.config import settings
    from app.room_service.chatbot.router import get_service, init_chatbot
    from app.room_service.chatbot.schemas import ChatAskRequest

    engine = create_engine(settings.database_url)
    init_chatbot(engine)
    service = get_service()
    if report.get('legal_only'):
        from legal_only_boundary import install
        report['cloud_boundary']=install(service,engine,report['cases'],settings.chatbot_legal_schema)
    analysis_client=getattr(getattr(service,'question_analyzer',None),'client',None)
    if analysis_client is not None:QUOTA.attach(analysis_client)
    verification_client=getattr(service.generator,'verifier',None)
    if verification_client is not None and verification_client is not analysis_client:QUOTA.attach(verification_client)
    if settings.chatbot_agents_enabled:
        from sqlalchemy import text
        import app.room_service.chatbot as chatbot_package
        pipeline_sha = pipeline_sha256(Path(chatbot_package.__file__).parent)
        if report.get('pipeline_sha256') and report['pipeline_sha256'] != pipeline_sha:
            raise ValueError('Generation pipeline changed; use a new evaluation output')
        report['pipeline_sha256'] = pipeline_sha
        with engine.connect() as conn:
            manifest_sha = conn.execute(text('SELECT manifest_sha256 FROM public.legal_corpus_releases WHERE schema_name=:schema'),
                                        {'schema':settings.chatbot_legal_schema}).scalar_one()
        if report.get('corpus_manifest_sha256') and report['corpus_manifest_sha256'] != manifest_sha:
            raise ValueError('Corpus changed; use a new evaluation output')
        report['corpus_manifest_sha256'] = manifest_sha
        configuration = {'agents_enabled':True,'legal_schema':settings.chatbot_legal_schema,
            'question_analysis_model':settings.chatbot_question_analysis_model,'answer_model':settings.ollama_model,
            'embedding_model':settings.chatbot_embedding_model,
            'analysis_provider_available':'gemini' if settings.configured_gemini_keys else 'rules-local',
            'legal_answer_mode':'source_select_then_synthesis' if settings.chatbot_answer_synthesis_enabled else 'source_select',
            'answer_synthesis_enabled':settings.chatbot_answer_synthesis_enabled,
            'answer_synthesis_model':(settings.chatbot_answer_synthesis_model or settings.gemini_model) if settings.chatbot_answer_synthesis_enabled else None}
        if report.get('run_configuration') and report['run_configuration'] != configuration:
            raise ValueError('Provider configuration changed; use a new evaluation output')
        report['run_configuration'] = configuration
    service.repo.record_event = lambda payload: None
    provider_calls = []
    for provider in getattr(service.generator, "providers", []):
        for method in ("generate", "check_legal_evidence"):
            if not hasattr(provider, method):
                continue
            original = getattr(provider, method)
            def traced(*args, _original=original, _provider=provider, _method=method, **kwargs):
                started = time.perf_counter()
                call = {"provider": _provider.provider_name, "model": _provider.model, "method": _method}
                try:
                    result = _original(*args, **kwargs)
                    call["success"] = True
                    if _method == "check_legal_evidence":
                        call["issues"] = len(result)
                        call['verification_issues'] = list(result)
                    elif kwargs.get('context_kind') == 'legal':
                        call['candidate_answer'] = result.text
                    return result
                except Exception as exc:
                    call.update(success=False, error_type=type(exc).__name__)
                    status = re.search(r"HTTP (\d{3})", str(exc))
                    if status:
                        call["http_status"] = int(status.group(1))
                    raise
                finally:
                    call["latency_ms"] = round((time.perf_counter() - started) * 1000)
                    provider_calls.append(call)
                    print(f"  {_provider.provider_name}/{_provider.model} {_method}: "
                          f"{call.get('http_status', 'ok' if call.get('success') else call.get('error_type'))} "
                          f"{call['latency_ms']}ms", flush=True)
            setattr(provider, method, traced)
    writer_client = getattr(getattr(service.generator, 'writer', None), 'client', None)
    if writer_client is not None:
        original_request = writer_client.request_json
        def traced_request(prompt, schema, **kwargs):
            started = time.perf_counter()
            stage = 'answer_synthesis' if 'summary' in schema.get('properties', {}) else 'source_verification'
            call = {'provider': 'gemini', 'model': writer_client.model, 'method': 'request_json', 'agent': stage}
            try:
                result = original_request(prompt, schema, **kwargs)
                call.update(success=True, usage=result[1])
                # Preserve the public-legal synthesis/check decision locally so
                # rule rejections can be diagnosed against the actual output.
                try:
                    call['structured_decision']=json.loads(result[0])
                except (ValueError,TypeError):
                    pass
                return result
            except Exception as exc:
                call.update(success=False, error_type=type(exc).__name__)
                raise
            finally:
                call['latency_ms'] = round((time.perf_counter() - started) * 1000)
                provider_calls.append(call)
                print(f"  gemini/{writer_client.model} {stage}: {'ok' if call.get('success') else call.get('error_type')} {call['latency_ms']}ms", flush=True)
        writer_client.request_json = traced_request
    prior = {case["id"]: case for case in report["cases"]}
    try:
        for case in report["cases"][:limit]:
            if ids is not None and case["id"] not in ids:
                continue
            if "answer" in case:
                continue
            history = []
            conversation_state = None
            # Questions 15 and 16 intentionally test follow-up memory after Q14.
            if case["category"] == "find_listing" and case["id"] in (15, 16, 17, 18):
                previous_ids = (14, 15) if case['id'] in (15, 16) else (14,)
                for previous_id in previous_ids:
                    if previous_id >= case["id"]:
                        break
                    previous = prior[previous_id]
                    if "answer" not in previous:
                        raise RuntimeError(f"Question {previous_id} must complete before {case['id']}")
                    history.extend([
                        {"role": "user", "content": previous["question"][:2000]},
                        {"role": "assistant", "content": previous["answer"][:2000]},
                    ])
                    conversation_state = previous.get('conversation_state')
            print(f"Collecting {case['id']:02d}/{len(report['cases'])} {case['category']}", flush=True)
            provider_calls.clear()
            try:
                result = service.ask(ChatAskRequest(
                    message=case["question"], conversation_history=history,
                    conversation_state=conversation_state,
                    include_evaluation_contexts=True,
                ))
                data = result.model_dump(mode="json")
                sources = data["sources"]
                case.update({
                    "answer": data["answer"],
                    "intent": data["intent"],
                    "confidence": data["confidence"],
                    "no_answer": data["no_answer"],
                    "partial_answer": data.get("partial_answer", False),
                    "degraded": data["degraded"],
                    "degraded_reasons": data["degraded_reasons"],
                    "retrieval_mode": data["retrieval_mode"],
                    "generation_provider": data["generation_provider"],
                    "generation_model": data["generation_model"],
                    "latency_ms": data["latency_ms"],
                    "provider_calls": list(provider_calls),
                    "agent_trace": data.get("agent_trace", []),
                    "corpus_schema": data.get("corpus_schema"),
                    "citation_accuracy": data["citation_accuracy"],
                    "contexts": [item["content"] for item in data["evaluation_contexts"]],
                    "sources": sources,
                    "listing_ids": [item["id"] for item in data["listings"]],
                    "listings": data['listings'],
                    "applied_filters": data.get('applied_filters'),
                    "conversation_state": data.get('conversation_state'),
                    "category_source_match": (
                        any(item.get("category") == case["category"] for item in sources)
                        if case["category"] != "find_listing" else None
                    ),
                })
                case.pop('error',None)
            except Exception as exc:
                case["error"] = f"collect: {type(exc).__name__}: {exc}"[:500]
                case["provider_calls"] = list(provider_calls)
                print(case["error"], flush=True)
            summarize(report)
            save_report(output, report)
    finally:
        engine.dispose()


def score(report: dict, output: Path, limit: int | None, judge_url: str, judge_model: str,
          selected_metrics: list[str], reset_selected_metrics: bool = False, ids: list[int] | None = None,
          score_abstentions: bool = False, judge_max_output_tokens: int = 2048,
          judge_provider: str = "ollama", score_workers: int = 1) -> None:
    import ragas
    import httpx
    from ragas.embeddings.base import BaseRagasEmbedding
    from ragas.llms.base import InstructorBaseRagasLLM
    from ragas.metrics.collections import AnswerRelevancy, ContextUtilization, Faithfulness
    from app.room_service.chatbot.providers import E5EmbeddingProvider

    class E5JudgeEmbeddings(BaseRagasEmbedding):
        def __init__(self, model_name: str):
            super().__init__()
            self.provider = E5EmbeddingProvider(model_name)

        def embed_text(self, text: str, **kwargs) -> list[float]:
            result = self.provider.embed_query(text)
            if result.vector is None:
                raise RuntimeError(result.degraded_reason or "E5 unavailable")
            return result.vector

        async def aembed_text(self, text: str, **kwargs) -> list[float]:
            return await asyncio.to_thread(self.embed_text, text, **kwargs)

    from ollama_judge import OllamaRagasLLM
    def local_judge():
        return OllamaRagasLLM(judge_url, judge_model, judge_max_output_tokens, 300)

    class GeminiRagasLLM(InstructorBaseRagasLLM):
        def __init__(self, model: str):
            from app.config import settings
            from app.room_service.chatbot.providers import GeminiGenerator
            self.model = model
            self.url = settings.gemini_base_url
            self.client = GeminiGenerator("", model, base_url=self.url, api_keys=settings.configured_gemini_keys,
                                          legal_timeout_seconds=180, per_request_timeout_seconds=180,
                                          min_request_interval_seconds=settings.gemini_min_request_interval_seconds)
            self.usage = []
            self.judgements = []
            QUOTA.attach(self.client)

        def generate(self, prompt: str, response_model: type):
            print(f"Gemini judge: {len(prompt)} characters, schema: {response_model.__name__}", flush=True)
            for attempt in range(2):
                try:
                    raw, usage = self.client.request_json(prompt, response_model.model_json_schema(),
                                                          max_output_tokens=judge_max_output_tokens)
                    break
                except RuntimeError as exc:
                    if attempt or not any(token in str(exc) for token in ("503", "429", "quá tải", "quota")):
                        raise
                    import time
                    if self.client._model_blocked_until - time.monotonic() > 60.5:
                        raise
                    time.sleep(min(60, max(1, self.client._model_blocked_until - time.monotonic() + .1)))
            self.usage.append({"prompt_eval_count": usage.get("promptTokenCount", 0),
                               "eval_count": usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)})
            parsed = response_model.model_validate_json(raw)
            self.judgements.append({"schema": response_model.__name__, "output": parsed.model_dump(mode="json")})
            return parsed

        async def agenerate(self, prompt: str, response_model: type):
            import asyncio
            return await asyncio.to_thread(self.generate, prompt, response_model)

    judge = GeminiRagasLLM(judge_model) if judge_provider == "gemini" else local_judge()
    embeddings = E5JudgeEmbeddings(os.getenv("CHATBOT_EMBEDDING_MODEL", "intfloat/multilingual-e5-small"))
    scorers = {
        "faithfulness": Faithfulness(llm=judge),
        "answer_relevancy": AnswerRelevancy(llm=judge, embeddings=embeddings, strictness=1),
        "context_utilization": ContextUtilization(llm=judge),
    }
    previous_judge = report.get("judge", {})
    metric_models = previous_judge.get("models_by_metric", {
        name: previous_judge.get("model") for name in METRIC_NAMES if previous_judge.get("model")
    })
    # Resuming must not relabel existing scores as produced by a different judge.
    previous_provider = previous_judge.get("provider", "ollama")
    for name in selected_metrics:
        existing = any(name in case.get("ragas", {}) for case in report["cases"]
                       if ids is None or case["id"] in ids)
        if existing and not reset_selected_metrics and (
                metric_models.get(name) != judge_model or previous_provider != judge_provider):
            raise ValueError("Existing scores use a different judge; clone the report or reset selected metrics explicitly")
    metric_models.update({name: judge_model for name in selected_metrics})
    report["judge"] = {"library": "ragas", "version": ragas.__version__, "model": judge_model,
                       "provider": judge_provider,
                       "score_workers": score_workers,
                       "models_by_metric": metric_models,
                       "embedding_model": embeddings.provider.model_name, "endpoint": judge.url,
                       "answer_relevancy_strictness": 1, "context_limit": 5,
                       "max_output_tokens": judge_max_output_tokens, "temperature": 0,
                       "judge_request_timeout_seconds": 180 if judge_provider == "gemini" else 300,
                       "context_char_limit": None, "score_abstentions": score_abstentions,
                       "context_policy": "all generation evidence; native model may still truncate its token window"}
    if reset_selected_metrics:
        for case in report["cases"]:
            if ids is not None and case["id"] not in ids:
                continue
            for name in selected_metrics:
                case.get("ragas", {}).pop(name, None)
                case.get("ragas_errors", {}).pop(name, None)
        summarize(report)
        save_report(output, report)
    if score_workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        local = threading.local()
        def score_task(case, name):
            if not hasattr(local, "judge"):
                local.judge = GeminiRagasLLM(judge_model) if judge_provider == "gemini" else local_judge()
                local.scorers = {
                    "faithfulness": Faithfulness(llm=local.judge),
                    "answer_relevancy": AnswerRelevancy(llm=local.judge, embeddings=embeddings, strictness=1),
                    "context_utilization": ContextUtilization(llm=local.judge),
                }
            usage_start = len(getattr(local.judge, "usage", []))
            judgement_start = len(getattr(local.judge, "judgements", []))
            kwargs = {"user_input": case["question"], "response": case["answer"]}
            if name != "answer_relevancy":
                kwargs["retrieved_contexts"] = [json.dumps({
                    "rank": source.get("rank"), "document": source.get("title"),
                    "category": source.get("category"), "heading": source.get("heading"),
                    "page_from": source.get("page_from"), "page_to": source.get("page_to"),
                    "content": context}, ensure_ascii=False)
                    for source, context in zip(case["sources"], case["contexts"])]
            error, value = None, None
            try:
                raw_value = float(local.scorers[name].score(**kwargs).value)
                value = round(raw_value, 4) if math.isfinite(raw_value) else None
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"[:500]
            usage = getattr(local.judge, "usage", [])[usage_start:]
            return value, error, {"max_output_tokens": judge_max_output_tokens, "requests": len(usage),
                "prompt_tokens": sum(item.get("prompt_eval_count") or 0 for item in usage),
                "output_tokens": sum(item.get("eval_count") or 0 for item in usage),
                "max_prompt_tokens": max((item.get("prompt_eval_count") or 0 for item in usage), default=0)}, getattr(local.judge, "judgements", [])[judgement_start:]
        tasks = []
        for case in report["cases"][:limit]:
                if ids is not None and case["id"] not in ids:
                    continue
                if "answer" not in case or (case.get("no_answer") and not score_abstentions) or not case.get("contexts"):
                    continue
                case.setdefault("ragas", {})
                case.setdefault("ragas_errors", {})
                for name in selected_metrics:
                    if isinstance(case["ragas"].get(name), (int, float)) and math.isfinite(case["ragas"][name]):
                        continue
                    case['ragas'].pop(name, None)
                    if name in case["ragas_errors"]:
                        case.setdefault("ragas_retry_history", []).append({"metric": name, "previous_error": case["ragas_errors"][name], "retry_max_output_tokens": judge_max_output_tokens})
                    tasks.append((case,name))
        def on_result(task,result):
                case, name = task
                value, error, usage, judgements = result
                case.setdefault("ragas_usage", {})[name] = usage
                case.setdefault("ragas_judgements", {})[name] = judgements
                if error:
                    case["ragas_errors"][name] = error
                elif value is not None:
                    case["ragas"][name] = value
                    case["ragas_errors"].pop(name, None)
                else:
                    case['ragas_errors'][name] = 'Judge returned a non-finite score; remains unscored'
                print(f"Saved {case['id']:02d}/{len(report['cases'])} {name}: {error or value}", flush=True)
                summarize(report)
                save_report(output, report)
        bounded_scoring(tasks,score_task,on_result,QUOTA,score_workers)
        return
    for case in report["cases"][:limit]:
        if ids is not None and case["id"] not in ids:
            continue
        if "answer" not in case or (case.get("no_answer") and not score_abstentions) or not case.get("contexts"):
            continue
        case.setdefault("ragas", {})
        case.setdefault("ragas_errors", {})
        user_input = case["question"]
        if case["category"] == "find_listing" and case["id"] in (15, 16):
            user_input = "Sau yêu cầu tìm phòng từ 18 m², có máy lạnh, giá không quá 2,5 triệu đồng/tháng: " + user_input
        for name in selected_metrics:
            scorer = scorers[name]
            if isinstance(case["ragas"].get(name), (int, float)) and math.isfinite(case["ragas"][name]):
                continue
            case['ragas'].pop(name, None)
            if name in case["ragas_errors"]:
                case.setdefault("ragas_retry_history", []).append({
                    "metric": name, "previous_error": case["ragas_errors"][name],
                    "retry_max_output_tokens": judge_max_output_tokens,
                })
            print(f"Scoring {case['id']:02d}/{len(report['cases'])} {name}", flush=True)
            usage_start = len(getattr(judge, "usage", []))
            judgement_start = len(getattr(judge, "judgements", []))
            try:
                kwargs = {"user_input": user_input, "response": case["answer"]}
                if name != "answer_relevancy":
                    kwargs["retrieved_contexts"] = [json.dumps({
                        "rank": source.get("rank"), "document": source.get("title"),
                        "category": source.get("category"), "heading": source.get("heading"),
                        "page_from": source.get("page_from"), "page_to": source.get("page_to"),
                        "content": context}, ensure_ascii=False)
                        for source, context in zip(case["sources"], case["contexts"])]
                value = float(scorer.score(**kwargs).value)
                case["ragas"][name] = round(value, 4) if math.isfinite(value) else None
                case["ragas_errors"].pop(name, None)
            except Exception as exc:
                case["ragas_errors"][name] = f"{type(exc).__name__}: {exc}"[:500]
                print(case["ragas_errors"][name], flush=True)
            case.setdefault("ragas_judgements", {})[name] = getattr(judge, "judgements", [])[judgement_start:]
            usage = getattr(judge, "usage", [])[usage_start:]
            case.setdefault("ragas_usage", {})[name] = {
                "max_output_tokens": judge_max_output_tokens,
                "requests": len(usage),
                "prompt_tokens": sum(item.get("prompt_eval_count") or 0 for item in usage),
                "output_tokens": sum(item.get("eval_count") or 0 for item in usage),
                "max_prompt_tokens": max((item.get("prompt_eval_count") or 0 for item in usage), default=0),
            }
            summarize(report)
            save_report(output, report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=Path("/question_bank.md"))
    parser.add_argument("--output", type=Path, default=Path("/eval/reports/question_bank_ragas_2026-10-01.json"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--phase", choices=("collect", "score", "all"), default="all")
    parser.add_argument("--judge-url", default=os.getenv("RAGAS_JUDGE_URL", "http://host.docker.internal:11434"))
    parser.add_argument("--judge-model", default=os.getenv("RAGAS_JUDGE_MODEL", "qwen3.5:9b"))
    parser.add_argument("--judge-provider", choices=("ollama", "gemini"), default=os.getenv("RAGAS_JUDGE_PROVIDER", "ollama"))
    parser.add_argument("--score-workers", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--judge-max-output-tokens", type=int, default=8192)
    parser.add_argument("--metrics", nargs="+", choices=METRIC_NAMES, default=list(METRIC_NAMES))
    parser.add_argument("--reset-selected-metrics", action="store_true")
    parser.add_argument("--ids", nargs="+", type=int, help="Chỉ chạy lại các câu cần sửa, giữ nguyên checkpoint khác")
    parser.add_argument("--score-abstentions", action="store_true", help="Chấm cả câu từ chối tổng hợp khi vẫn có ngữ cảnh; không giả lập điểm 0")
    args = parser.parse_args()
    questions = load_questions(args.questions)
    digest = hashlib.sha256(args.questions.read_bytes()).hexdigest()
    if args.output.exists():
        report = json.loads(args.output.read_text(encoding="utf-8"))
        if report.get("question_bank_sha256") != digest:
            raise ValueError("Question bank changed; choose a new output file")
    else:
        report = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
                  "question_bank_sha256": digest,
                  "method": "real DB + configured provider chain + Ragas common judge; no independent references",
                  "cases": questions}
    if args.ids:
        selected = set(args.ids)
        unknown = selected - {case["id"] for case in report["cases"]}
        if unknown:
            parser.error(f"Unknown IDs: {sorted(unknown)}")
    report.pop('quota_state',None)
    try:
        if args.phase in ("collect", "all"):
            collect(report, args.output, args.limit, args.ids)
        if args.phase in ("score", "all"):
            score(report, args.output, args.limit, args.judge_url, args.judge_model, args.metrics,
                  args.reset_selected_metrics, args.ids, args.score_abstentions, args.judge_max_output_tokens,
                  args.judge_provider, args.score_workers)
    except QuotaPause:
        checkpoint_pause(report,args.output,QUOTA,args.phase)
        print('HTTP 429: saved checkpoint; wait until '+report['quota_state']['retry_at_utc'],flush=True)
        raise SystemExit(75)
    summarize(report)
    report["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    save_report(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
