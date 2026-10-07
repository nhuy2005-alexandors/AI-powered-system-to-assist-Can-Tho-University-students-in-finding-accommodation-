"""Replay the legal bank through the serving Gemini/Qwen flow, without user cache.

Records answers, citations and verification, not a fabricated RAGAS score.
Each completed case is checkpointed. Resume requires identical code and corpus.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/api'))
from sqlalchemy import create_engine, text
from app.config import settings
from app.room_service.chatbot.router import init_chatbot, get_service, close_chatbot
from app.room_service.chatbot.schemas import ChatAskRequest
import app.room_service.chatbot as chatbot_package


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--questions', type=Path, default=ROOT / 'eval/datasets/legal_question_bank.txt')
    parser.add_argument('--output', type=Path, default=ROOT / 'eval/reports/legal36_retest_20261007.json')
    parser.add_argument('--ids', nargs='+', type=int)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    cases, category = [], None
    for line in args.questions.read_text(encoding='utf-8').splitlines():
        if line.startswith('### ') and (m := re.search(r'`([a-z_]+)`', line)):
            category = m[1]
        if m := re.match(r'^(\d+)\.\s+(.+)$', line):
            cases.append(dict(id=int(m[1]), question=m[2], category=category))
    assert [c['id'] for c in cases] == list(range(1, 37))
    engine = create_engine(settings.database_url)
    init_chatbot(engine)
    service = get_service()
    service.repo.record_event = lambda payload: None
    pipeline = Path(chatbot_package.__file__).parent
    # This runner bypasses the HTTP history/cache boundary. Changes there do
    # not alter the retrieval/generation flow exercised by independent cases.
    pipeline_files = sorted(p for p in pipeline.glob('*.py') if p.name != 'history.py')
    with engine.connect() as conn:
        manifest = conn.execute(text('SELECT manifest_sha256 FROM public.legal_corpus_releases WHERE schema_name=:s'),
                                {'s': settings.chatbot_legal_schema}).scalar_one()
    identity = dict(legal_schema=settings.chatbot_legal_schema, graph_schema=settings.chatbot_graph_schema,
                    manifest_sha256=manifest, questions_sha256=hashlib.sha256(args.questions.read_bytes()).hexdigest(),
                    pipeline_sha256=hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in pipeline_files)).hexdigest(),
                    pipeline_files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in pipeline_files},
                    agents_enabled=settings.chatbot_agents_enabled, synthesis_enabled=settings.chatbot_answer_synthesis_enabled,
                    answer_model=settings.ollama_model, embedding_model=settings.chatbot_embedding_model,
                    analysis_model=settings.chatbot_question_analysis_model,
                    synthesis_model=settings.chatbot_answer_synthesis_model or settings.gemini_model,
                    confidence_threshold=settings.chatbot_confidence_threshold,max_results=settings.chatbot_max_results)
    report = dict(identity=identity, started_at=datetime.now(timezone.utc).isoformat(), cases=cases,
                  mode='real serving service; independent questions; no saved history/cache; no RAGAS grading')
    if args.resume and args.output.exists():
        report = json.loads(args.output.read_text(encoding='utf-8'))
        if report['identity'] != identity:
            raise ValueError('Cannot mix code/corpus/configurations in one run')
    try:
        # Reproduce the reported failures first, then run all remaining cases.
        ordered = sorted(report['cases'], key=lambda c: (c['id'] not in (25, 26, 27, 28), c['id']))
        for case in ordered:
            if 'answer' in case or (args.ids and case['id'] not in args.ids):
                continue
            print(f"START {case['id']:02d}/36", flush=True)
            try:
                result = service.ask(ChatAskRequest(message=case['question']))
                case.update(result.model_dump(mode='json'))
                case['category_source_match'] = any(s.category == case['category'] for s in result.sources)
                case['status'] = ('complete' if not result.no_answer else
                                  'partial' if result.sources and result.partial_answer else 'insufficient')
                case.pop('error', None)
            except Exception as exc:
                case.update(status='error', error=type(exc).__name__)
            completed = [c for c in report['cases'] if 'answer' in c]
            report['summary'] = dict(completed=len(completed), total=36,
                complete=sum(c['status']=='complete' for c in completed),
                partial=sum(c['status']=='partial' for c in completed),
                insufficient=sum(c['status']=='insufficient' for c in completed),
                with_sources=sum(bool(c['sources']) for c in completed),
                errors=sum(c.get('status')=='error' for c in report['cases']))
            report['updated_at'] = datetime.now(timezone.utc).isoformat()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            temporary.replace(args.output)
            print(json.dumps(dict(id=case['id'],status=case['status'],sources=len(case.get('sources', [])),
                                  provider=case.get('generation_provider'),latency_ms=case.get('latency_ms'),
                                  summary=report['summary'])), flush=True)
    finally:
        close_chatbot()
        engine.dispose()


if __name__ == '__main__':
    main()
