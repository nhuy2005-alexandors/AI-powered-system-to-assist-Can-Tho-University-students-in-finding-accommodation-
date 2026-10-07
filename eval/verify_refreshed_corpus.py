"""Verify fresh manifest integrity, exact reviewed excerpts and labelled guidance."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / 'apps/api/app').is_dir(): ROOT = Path('/workspace')
CORPUS = ROOT / 'docs/legal_corpus_v3_20261004'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))

manifest = read(CORPUS / 'manifest.json')
documents, provisions, categories, guidance_questions = [], [], Counter(), []
ids = set()
for entry in manifest['documents']:
    path = (ROOT / entry['file']).resolve()
    assert path.parent == CORPUS.resolve()
    assert sha(path) == entry['sha256'], entry['id']
    doc = read(path)
    assert doc['source']['id'] == entry['id'] and entry['id'] not in ids
    assert doc['source']['category'] == entry['category'] != 'review_before_category_assignment'
    assert len(doc['provisions']) == entry['provisions'] > 0
    ids.add(entry['id'])
    categories[entry['category']] += 1
    for provision in doc['provisions']:
        assert provision['content'].strip() and provision['provision_id']
        assert provision.get('page_from', 0) > 0
        if provision.get('content_sha256'):
            assert hashlib.sha256(provision['content'].encode()).hexdigest() == provision['content_sha256']
        if doc['source'].get('page_kind') == 'editorial_guidance':
            assert provision['kind'] == 'editorial_guidance'
            assert provision['content'].startswith('HƯỚNG DẪN BIÊN SOẠN')
            guidance_questions.extend(re.findall(r'(?m)^### Q: (.+)$', provision['content']))
        provisions.append(provision)
    documents.append(doc)
for relative, digest in manifest['input_sha256'].items():
    assert sha(ROOT / relative) == digest, relative
candidate = read(ROOT / 'docs/legal_web_supplement_20261004/candidate_corpus/manifest.json')
reviewed = [p for entry in candidate['documents'] for p in read(ROOT / entry['file'])['provisions']]
assert all(any(p['provision_id'] == q['provision_id'] and p['content'] == q['content'] for q in provisions) for p in reviewed)
bank = (ROOT / 'eval/datasets/legal_question_bank.txt').read_text(encoding='utf-8')
questions = [m[1] for line in bank.splitlines() if (m := re.match(r'^\d+\. (.+)$', line))]
assert len(questions) == 36
exact_overlap = set(questions) & set(guidance_questions)
assert len(exact_overlap) == 35, 'Unexpected guidance/question overlap; inspect the changed question bank'
reference = 'eval/datasets/external_legal_20261004/answers.json'
assert reference not in manifest['input_sha256']
report = dict(passed=True, schema=manifest['schema'], manifest_sha256=sha(CORPUS / 'manifest.json'),
    documents=len(documents), provisions=len(provisions), categories=dict(categories),
    reviewed_new_excerpts_preserved=len(reviewed), exact_question_header_overlap=len(exact_overlap),
    questions_without_exact_guidance_header=sorted(set(questions)-set(guidance_questions)),
    input_hashes_verified=len(manifest['input_sha256']), user_reference_not_indexed=True,
    evaluation_note='35 question headers match exactly; the platform-responsibility topic is phrased differently. Regression on known topics, not an unseen benchmark')
(ROOT / 'eval/reports/legal_refresh_corpus_integrity_2026-10-04.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
