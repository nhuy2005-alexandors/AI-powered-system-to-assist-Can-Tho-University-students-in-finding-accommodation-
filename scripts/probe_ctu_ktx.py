"""Exercise serving chatbot with real retrieval, generation and verification."""
from pathlib import Path
import json
import sys
import time
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/api'))
from sqlalchemy import create_engine
from app.config import settings
from app.room_service.chatbot.router import init_chatbot, get_service, close_chatbot
from app.room_service.chatbot.schemas import ChatAskRequest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--question', action='append', help='Run only these KTX questions')
    args = parser.parse_args()
    engine = create_engine(settings.database_url)
    init_chatbot(engine)
    service = get_service()
    output = ROOT / 'eval/reports/ctu_ktx_answers_20261007.json'
    records = []
    if args.resume and output.exists():
        previous = json.loads(output.read_text(encoding='utf-8'))
        if previous['schema'] != settings.chatbot_legal_schema:
            raise ValueError('Cannot resume against another corpus')
        records = previous['results']
    questions = args.question or [
        'KTX CTU có wifi không và phí gửi xe máy bao nhiêu?',
        'Phí ở KTX khu A và khu B của CTU bao nhiêu một tháng?',
        'Tân sinh viên đăng ký KTX CTU như thế nào?',
        'KTX CTU thu tiền điện nước như thế nào?',
        'Trả chỗ KTX CTU trước hạn có được hoàn phí không?',
        'KTX CTU có được nấu ăn không?',
    ]
    try:
        for question in questions:
            if any(r['question'] == question for r in records):
                continue
            started = time.monotonic()
            result = service.ask(ChatAskRequest(message=question))
            record = dict(question=question, answer=result.answer, no_answer=result.no_answer,
                provider=result.generation_provider, latency_seconds=round(time.monotonic()-started, 2),
                agent_trace=result.agent_trace,
                sources=[dict(title=s.title, category=s.category, url=s.source_url) for s in result.sources])
            records.append(record)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(dict(schema=settings.chatbot_legal_schema, results=records), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            print(json.dumps(record, ensure_ascii=False), flush=True)
            # A sourced partial answer is valid when CTU has not published
            # requested details (e.g. a per-kWh tariff). Keep that limitation
            # and the API's no_answer flag in the report instead of inventing it.
            if not any(s.category == 'student_housing' for s in result.sources) or not result.answer.strip():
                raise AssertionError('KTX question must have a sourced answer: ' + question)
    finally:
        close_chatbot()
        engine.dispose()


if __name__ == '__main__':
    main()
