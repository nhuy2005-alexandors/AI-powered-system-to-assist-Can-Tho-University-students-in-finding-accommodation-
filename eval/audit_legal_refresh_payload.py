"""Confirm evaluation payload text was already published in the user's repository."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '432aed25f4bae151738449b9c10d620df6f0840b'
manifest = json.loads((ROOT / 'docs/legal_corpus_v3_20261004/manifest.json').read_text(encoding='utf-8'))
paths = list(manifest['input_sha256']) + ['docs/LEGAL_QUESTION_BANK.md',
    'eval/datasets/external_legal_20261004/answers.json']
unpublished, changed, markers = [], [], []
for relative in paths:
    result = subprocess.run(['git', 'show', BASELINE + ':' + relative], cwd=ROOT, capture_output=True)
    # Compare the unchanged bank bytes against their historical Git path.
    actual = 'eval/datasets/legal_question_bank.txt' if relative == 'docs/LEGAL_QUESTION_BANK.md' else relative
    content = (ROOT / actual).read_bytes()
    if result.returncode:
        unpublished.append(relative)
    elif result.stdout.replace(b'\r\n', b'\n') != content.replace(b'\r\n', b'\n'):
        changed.append(relative)
    decoded = content.decode('utf-8')
    for marker in ('Datehouse', 'housing_cases_', '@example.test', 'GEMINI_API_KEY=', 'JWT_SECRET='):
        if marker in decoded: markers.append(dict(file=relative, marker=marker))
questions = (ROOT / 'eval/datasets/legal_question_bank.txt').read_text(encoding='utf-8')
report = dict(public_repository='https://github.com/phucbeo223/Local-Project-For-Student-Room',
    public_baseline_commit=BASELINE, input_files_checked=len(paths), unpublished_inputs=unpublished,
    changed_since_publication=changed, private_or_secret_marker_hits=markers,
    questions=sum(bool(re.match(r'^\d+\. ', line)) for line in questions.splitlines()),
    runtime_destination='Configured local Gemini-compatible proxy at http://host.docker.internal/v1beta; downstream provider is not independently verified',
    evaluation_scope='36 generic legal questions; legal_v3_20261004 only. No rental listings, Datehouse, authentication rows, .env files, or housing case reports in prompts.',
    generation_reference_isolation='User answers are loaded only by the separate comparison stage after generation.',
    corpus_kind='Public legal texts and public student guidance, including published government contact details. Prepared source metadata labels editorial guidance.',
    passed=not unpublished and not changed and not markers)
(ROOT / 'eval/reports/legal_refresh_payload_audit_2026-10-04.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
if not report['passed']: raise SystemExit(2)
