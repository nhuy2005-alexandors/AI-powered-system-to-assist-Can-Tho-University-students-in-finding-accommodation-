"""Record a reproducible model upgrade without including credentials."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent
ROOT = Path("/workspace") if Path("/workspace/apps/api/app").exists() else EVAL_ROOT.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before, after = [json.loads(p.read_text(encoding="utf-8")) for p in (args.before, args.after)]
    original = args.before.parent / "legal_question_bank_release_2026-10-01.json"
    archive = json.loads(original.read_text(encoding="utf-8"))
    immutable = all(
        {k: v for k, v in old.items() if k not in {"ragas", "ragas_errors", "ragas_usage", "ragas_retry_history", "ragas_judgements"}}
        == {k: v for k, v in new.items() if k not in {"ragas", "ragas_errors", "ragas_usage", "ragas_retry_history", "ragas_judgements", "archived_evaluation"}}
        for old, new in zip(archive["cases"], before["cases"])
    ) and len(archive["cases"]) == len(before["cases"])
    if not immutable or digest(original) != before["archived_baseline"]["sha256"]:
        raise ValueError("Archived baseline changed")
    app_files = sorted((ROOT / "apps/api/app/room_service/chatbot").glob("*.py"))
    app_files += sorted((ROOT / "apps/api/app/room_service/legal_knowledge").glob("*.py"))
    files = [ROOT / "apps/api/app/config.py", ROOT / "docker-compose.yml",
             ROOT / "docker-compose.override.yml", ROOT / "docker-compose.ragas.yml",
             *app_files]
    source_hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in files}
    for name in ("question_bank_ragas.py", "compare_model_upgrade.py", "stamp_model_upgrade.py"):
        source_hashes["eval/" + name] = digest(EVAL_ROOT / name)
    question_path = Path("/question_bank.md") if Path("/question_bank.md").exists() else ROOT / "eval/datasets/legal_question_bank.txt"
    source_hashes["eval/datasets/legal_question_bank.txt"] = digest(question_path)
    data_root = Path("/data") if Path("/data").exists() else ROOT / "Data"
    data = sorted(p for p in data_root.rglob("*") if p.is_file())
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "question_bank_sha256": after["question_bank_sha256"],
        "baseline_immutable": immutable,
        "run_sha256": {args.before.name: digest(args.before), args.after.name: digest(args.after)},
        "source_sha256": source_hashes,
        "data_sha256": {p.relative_to(data_root).as_posix(): digest(p) for p in data},
        "hardware": {"cpu": "AMD Ryzen 5 7535HS", "ram_bytes": 16312721408,
                     "gpu": "NVIDIA RTX 4050 Laptop", "vram_mib": 6141},
        "local_model": {"installed": "qwen3.5:9b", "quantization": "Q4_K_M",
                        "removed": ["qwen3.5:4b", "qwen2.5:1.5b"],
                        "smoke_latency_seconds": 25.44, "smoke_tokens_per_second": 7.52,
                        "smoke_context": 8192, "smoke_gpu_resident_bytes": 5636882430},
        "effective_configuration": {"provider": "auto", "order": ["gemini", "qwen", "template"],
                                    "gemini_model": "gemini-3.5-flash-lite", "ollama_model": "qwen3.5:9b",
                                    "llm_timeout_seconds": 60, "legal_timeout_seconds": 180,
                                    "max_output_tokens": 1536, "ollama_context_length": 8192},
        "credential_probes": {"slot_1": "HTTP 503 on inference", "slot_2": "HTTP 403 project denied",
                              "slot_3": "Gemini 3.8 first succeeded then daily quota 20; Gemini 3.5 Flash Lite schema and Ragas succeeded"},
        "judge_before": before.get("judge"), "judge_after": after.get("judge"),
        "score_coverage": {"before": before["summary"]["ragas"], "after": after["summary"]["ragas"]},
        "score_errors": {label: [{"id": c["id"], "errors": c["ragas_errors"]}
                                 for c in run["cases"] if c.get("ragas_errors")]
                         for label, run in (("before", before), ("after", after))},
        "regression": {"passed": 89, "failed": 0},
        "incremental_source_guard_retest": after.get("incremental_source_guard_retest"),
        "known_input_gap": {"case_id": 4, "source": "housing_contract/Bộ-luật-91-2015-QH13-trích-tuyển.docx",
                            "issue": "Article 328 clause 2 ends at trừ trườ in both input DOCX and retrieved context; no source completion invented"},
        "runtime_verification": {"api_health": "ok", "configured_key_count": 3,
            "api_image": "sha256:2f8626d1841bac29dbb66a4e728e94537cefc12ec4c79717c01577a8509fd2a0",
            "electricity_smoke": {"intent": "legal_question", "provider": "legal-extractive",
                                  "no_answer": False, "sources": 3, "citation_accuracy": 1.0,
                                  "retrieval_mode": "legal_hybrid"}},
        "verification_optimization": "Cited ranks mapped to deduplicated full sources; no regeneration on verifier outage",
        "limits": ["No independent reference answers: correctness and recall unmeasured",
                   "Common Gemini judge may favor Gemini-generated answers",
                   "Native faithfulness also judges disclaimers; some verdicts misread editorial source notes. All verdicts retained without score adjustment",
                   "Model, retrieval and checking changed together; not a model-only causal experiment",
                   "Cloud overload and local fallback affect latency",
                   "Baseline scoring overlapped early collection until paused; shared quota affected two local fallbacks",
                   "Initial and local partial trials preserved separately; final run uses available Gemini 3.5 Flash Lite"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
