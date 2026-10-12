import json
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ragas_eval import collect, load_cases, summarize


def test_collection_endpoint_contexts_errors_resume_and_source_checks(tmp_path):
    cases = [{"id": "ok", "question": "Tìm phòng trọ"}, {"id": "bad", "question": "Câu lỗi"}]
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/admin/documents/evaluation-manifest":
            return httpx.Response(200, json={"corpus_snapshot_sha256": "stable"})
        assert request.url.path == "/chatbot/ask"
        payload = json.loads(request.content)
        assert payload["include_evaluation_contexts"] is True
        if payload["message"] == "Câu lỗi":
            return httpx.Response(500, json={"detail": "test failure"})
        return httpx.Response(200, json={
            "answer": "Phòng đã tìm thấy [1]", "sources": [{"rank": 1}], "listings": [],
            "citation_applicable": True, "partial_answer": True,
            "evaluation_contexts": [{"rank": 1, "content": "Phòng trọ"}],
        })
    report = {"cases": cases.copy()}
    output = tmp_path / "report.json"
    with httpx.Client(base_url="http://feature.test", transport=httpx.MockTransport(handler)) as client:
        collect(client, cases, report, output)
        first_asks = calls.count("/chatbot/ask")
        collect(client, cases, report, output)
    assert first_asks == 2 and calls.count("/chatbot/ask") == 3
    summary = summarize(report)
    assert summary["completed"] == 1 and summary["errors"] == 1
    assert summary["partial_answer_rate"] == 1
    assert summary["citation_format_accuracy_mean"] == 1
    assert summary["ragas"]["faithfulness"]["mean"] is None
    assert json.loads(output.read_text(encoding="utf-8"))["summary"]["errors"] == 1


def test_manifest_change_refuses_to_mix_runs(tmp_path):
    report = {"server_manifest": {"version": 1}, "cases": []}
    client = httpx.Client(base_url="http://feature.test", transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json={"version": 2})))
    with client, pytest.raises(ValueError, match="Model/corpus"):
        collect(client, [], report, tmp_path / "report.json")


def test_dataset_ids_and_no_zero_for_missing_scores(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text('{"id":"1","question":"a"}\n{"id":"1","question":"b"}', encoding="utf-8")
    with pytest.raises(ValueError, match="id"):
        load_cases(path)
    report = {"cases": [{"id": 1, "error": "offline", "latency_ms": 10}]}
    summary = summarize(report)
    assert summary["error_rate"] == 1
    assert summary["citation_format_accuracy_mean"] is None
    assert summary["ragas"]["faithfulness"]["scored"] == 0
