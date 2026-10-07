"""Start an empty versioned evaluation without probing an already known quota."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib
from question_bank_ragas import save_report,summarize

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prior',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Output already exists; resume it instead')
    root=Path(__file__).resolve().parents[1]
    old=json.loads(args.prior.read_text(encoding='utf-8'))
    if any('answer' in c for c in old['cases']):raise ValueError('Only an empty quota checkpoint can seed a fresh run')
    bank=root/'eval/datasets/legal_question_bank.txt'
    if hashlib.sha256(bank.read_bytes()).hexdigest()!=old['question_bank_sha256']:raise ValueError('Question bank changed')
    files=sorted((root/'apps/api/app/room_service/chatbot').glob('*.py'))
    report={'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'question_bank_sha256':old['question_bank_sha256'],'method':old['method'],
        'cases':[{k:c[k] for k in ('id','question','category')} for c in old['cases']],
        'quota_state':old['quota_state'],'run_configuration':old['run_configuration'],
        'pipeline_sha256':hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in files)).hexdigest(),
        'corpus_manifest_sha256':hashlib.sha256((root/'docs/legal_corpus_v2/manifest.json').read_bytes()).hexdigest(),
        'inherited_quota_checkpoint':{'path':str(args.prior),
            'sha256':hashlib.sha256(args.prior.read_bytes()).hexdigest(),
            'reason':'Same Gemini project daily quota; zero answers/scores, no additional request before retry'}}
    summarize(report);save_report(args.output,report)
    print('Fresh checkpoint: zero answers/scores; wait until '+report['quota_state']['retry_at_utc'])

if __name__=='__main__':main()
