"""Clone the serving corpus and graph, adding real E5 dormitory embeddings.

The source release and listing rows remain intact. Re-running the same input is
safe; a different input requires a new target release. Run inside the API image
with the repository mounted/copied at /workspace, then apply the KTX override.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/api'))
from sqlalchemy import create_engine, text
from app.config import settings
from app.room_service.chatbot.graph_retrieval import GraphChatRepository, graph_schema
from app.room_service.chatbot.providers import E5EmbeddingProvider
from app.room_service.legal_knowledge.chunker import LegalChunk
from app.room_service.legal_knowledge.extractor import ExtractedDocument, ExtractedPage
from app.room_service.legal_knowledge.repo import LegalKnowledgeRepository
from app.room_service.legal_knowledge.storage import legal_schema
from index_legal_agent_corpus import pieces


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(conn, schema):
    return {table: dict(conn.execute(text(f'SELECT count(*) AS rows, '
        f"md5(string_agg(row_to_json(t)::text,'|' ORDER BY id)) AS digest FROM {schema}.{table} t"
        )).mappings().one()) for table in ('legal_documents', 'legal_chunks')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema', default='legal_ctu_ktx_v2_20261007')
    parser.add_argument('--graph-schema', default='graph_ctu_ktx_v2_20261007')
    # Keep the already indexed legal/guidance supplements when adding KTX.
    # Serving settings point at the target after activation, not its base.
    parser.add_argument('--base-schema', default='legal_word_repair_v16_20261006')
    parser.add_argument('--base-graph-schema', default='graph_rag_word_repair_v16')
    parser.add_argument('--listing-schema', default='housing_graph_word_repair_v16')
    parser.add_argument('--corpus', type=Path, default=ROOT / 'docs/ctu_ktx_corpus_20261007')
    parser.add_argument('--report', type=Path, default=ROOT / 'eval/reports/ctu_ktx_v2_index_20261007.json')
    args = parser.parse_args()
    target, graph = legal_schema(args.schema), graph_schema(args.graph_schema)
    base, base_graph = legal_schema(args.base_schema), graph_schema(args.base_graph_schema)
    listing = args.listing_schema
    if target == 'public' or target == base or graph == base_graph:
        raise ValueError('Use new, isolated target schemas')
    engine = create_engine(settings.database_url)
    # Validate the serving graph before copying it.
    GraphChatRepository(engine, base, listing, base_graph)
    manifest_path = args.corpus / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    with engine.begin() as conn:
        before = snapshot(conn, base)
        base_hash = conn.execute(text('SELECT manifest_sha256 FROM public.legal_corpus_releases WHERE schema_name=:s'), {'s': base}).scalar_one()
        release_hash = hashlib.sha256((base_hash + digest(manifest_path)).encode()).hexdigest()
        existing = conn.execute(text('SELECT manifest_sha256 FROM public.legal_corpus_releases WHERE schema_name=:s'), {'s': target}).scalar_one_or_none()
        if existing and existing != release_hash:
            raise ValueError('Target has different inputs; choose a new release')
        if not existing:
            migration = (ROOT / 'infra/db/migrations/101_isolated_legal_corpus.sql').read_text(encoding='utf-8')
            conn.exec_driver_sql(migration.replace('legal_v2', target))
            for table in ('legal_documents', 'legal_chunks'):
                # Explicit columns also support older serving releases.
                columns = list(conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema=:s AND table_name=:t AND is_generated='NEVER' ORDER BY ordinal_position"),
                    {'s': base, 't': table}).scalars())
                if table == 'legal_documents' and 'admin_enabled' in columns:
                    # The additive admin migration may predate this new release.
                    # Preserve suspended sources when cloning the base corpus.
                    conn.execute(text(f'ALTER TABLE {target}.legal_documents ADD COLUMN IF NOT EXISTS admin_enabled BOOLEAN NOT NULL DEFAULT true'))
                names = ','.join('"' + c + '"' for c in columns)
                conn.execute(text(f'INSERT INTO {target}.{table} ({names}) SELECT {names} FROM {base}.{table}'))
            for sequence, table in (('document_id', 'legal_documents'), ('chunk_id', 'legal_chunks')):
                conn.execute(text(f"SELECT setval('{target}.{sequence}', COALESCE((SELECT max(id) FROM {target}.{table}),0)+1,false)"))
            conn.execute(text('UPDATE public.legal_corpus_releases SET manifest_sha256=:h,validation=CAST(:v AS jsonb) WHERE schema_name=:s'),
                {'h': release_hash, 's': target, 'v': json.dumps(dict(base_schema=base, base_hash=base_hash, ktx_manifest_sha256=digest(manifest_path)))})
    repo = LegalKnowledgeRepository(engine, target)
    embedder = E5EmbeddingProvider(settings.chatbot_embedding_model)
    indexed = []
    for entry in manifest['documents']:
        path = ROOT / entry['file']
        if digest(path) != entry['sha256']:
            raise ValueError('Source checksum mismatch: ' + entry['id'])
        data = json.loads(path.read_text(encoding='utf-8'))
        source = data['source']
        if digest(ROOT / source['path']) != source['original_sha256']:
            raise ValueError('Original checksum mismatch: ' + entry['id'])
        if repo.current_hash(entry['file']) == entry['sha256']:
            continue
        parents, chunks = [], []
        for parent in data['provisions']:
            assert hashlib.sha256(parent['content'].encode()).hexdigest() == parent['content_sha256']
            for content in pieces(parent):
                chunks.append(LegalChunk(len(chunks), parent['page_from'], parent['page_to'], parent['heading'], content,
                                         hashlib.sha256(content.encode()).hexdigest()))
                parents.append(parent)
        vectors = []
        for start in range(0, len(chunks), 24):
            vectors.extend(embedder.embed_passages([source['title'] + '\n' + c.heading + '\n' + c.content for c in chunks[start:start+24]]))
        if len(vectors) != len(chunks) or not all(len(v) == 384 for v in vectors):
            raise ValueError('Incomplete E5 embeddings')
        doc = ExtractedDocument(path, entry['file'], source['title'], 'student_housing', 'structured_json',
            'application/json', entry['sha256'], tuple(ExtractedPage(i, '', False) for i in range(1, source['pages']+1)), None)
        doc_id = repo.replace_document(doc, chunks, vectors, settings.chatbot_embedding_model)
        with engine.begin() as conn:
            conn.execute(text(f'UPDATE {target}.legal_documents SET source_metadata=CAST(:m AS jsonb) WHERE id=:id'),
                {'id': doc_id, 'm': json.dumps(source, ensure_ascii=False)})
            for i, parent in enumerate(parents):
                conn.execute(text(f'UPDATE {target}.legal_chunks SET provision_id=:pid,parent_content=:p,source_metadata=CAST(:m AS jsonb) WHERE document_id=:id AND chunk_index=:i'),
                    {'id': doc_id, 'i': i, 'pid': parent['provision_id'], 'p': parent['content'],
                     'm': json.dumps({k: v for k, v in parent.items() if k != 'content'}, ensure_ascii=False)})
        indexed.append(dict(id=source['id'], chunks=len(chunks)))
        print('indexed', source['id'], len(chunks), flush=True)
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('graph-rag-release-v1'))"))
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {graph}'))
        for table in ('release', 'nodes', 'edges'):
            conn.execute(text(f'CREATE TABLE IF NOT EXISTS {graph}.{table} (LIKE {base_graph}.{table} INCLUDING ALL)'))
        existing = conn.execute(text(f'SELECT legal_sha256 FROM {graph}.release WHERE id=1')).scalar_one_or_none()
        if existing and existing != release_hash:
            raise ValueError('Graph target has different inputs')
        if not existing:
            for table in ('release', 'nodes', 'edges'):
                conn.execute(text(f'INSERT INTO {graph}.{table} SELECT * FROM {base_graph}.{table}'))
            conn.execute(text(f'UPDATE {graph}.release SET legal_schema=:s,legal_sha256=:h,created_at=now() WHERE id=1'), {'s': target, 'h': release_hash})
            rows = conn.execute(text(f'SELECT DISTINCT ON(c.document_id,c.provision_id) c.document_id,c.provision_id,c.heading,d.title FROM {target}.legal_chunks c JOIN {target}.legal_documents d ON d.id=c.document_id WHERE d.category=\'student_housing\' AND d.status=\'ready\' ORDER BY c.document_id,c.provision_id')).mappings().all()
            conn.execute(text(f"INSERT INTO {graph}.nodes(id,kind,label) VALUES('topic:student_housing','topic','student_housing') ON CONFLICT DO NOTHING"))
            for row in rows:
                document = f"document:{row['document_id']}"
                provision = f"legal:{row['document_id']}:{row['provision_id']}"
                for node_id, kind, label, pid in ((document, 'document', row['title'], None), (provision, 'provision', row['heading'], row['provision_id'])):
                    conn.execute(text(f'INSERT INTO {graph}.nodes(id,kind,document_id,provision_id,label) VALUES(:id,:k,:d,:p,:l) ON CONFLICT DO NOTHING'),
                        {'id': node_id, 'k': kind, 'd': row['document_id'], 'p': pid, 'l': label})
                for origin, destination, relation in ((provision, document, 'belongs_to'), (document, 'topic:student_housing', 'covers')):
                    conn.execute(text(f'INSERT INTO {graph}.edges(source,target,relation,evidence) VALUES(:s,:t,:r,CAST(:e AS jsonb)) ON CONFLICT DO NOTHING'),
                        {'s': origin, 't': destination, 'r': relation, 'e': json.dumps(dict(manifest_sha256=release_hash, document_id=row['document_id'], provision_id=row['provision_id']))})
        counts = dict(conn.execute(text(f"SELECT count(*) AS chunks,count(c.embedding_vector) AS vectors,count(DISTINCT d.id) AS documents FROM {target}.legal_chunks c JOIN {target}.legal_documents d ON d.id=c.document_id WHERE d.category='student_housing' AND d.status='ready' ")).mappings().one())
        assert counts['documents'] == len(manifest['documents']) and counts['chunks'] == counts['vectors'] > 0
        total = dict(conn.execute(text(f"SELECT count(*) AS chunks,count(c.embedding_vector) AS vectors,count(DISTINCT d.id) AS documents FROM {target}.legal_chunks c JOIN {target}.legal_documents d ON d.id=c.document_id WHERE d.status='ready'")).mappings().one())
        assert total['chunks'] == total['vectors'], 'Every serving chunk needs a real embedding'
        categories = [dict(r) for r in conn.execute(text(f'SELECT d.category,count(DISTINCT d.id) AS documents,count(c.id) AS chunks FROM {target}.legal_documents d JOIN {target}.legal_chunks c ON c.document_id=d.id WHERE d.status=\'ready\' GROUP BY d.category ORDER BY d.category')).mappings()]
        after = snapshot(conn, base)
        assert before == after, 'Serving corpus changed while indexing'
        conn.execute(text("UPDATE public.legal_corpus_releases SET status='validated' WHERE schema_name=:s AND status='staging'"), {'s': target})
    GraphChatRepository(engine, target, listing, graph)
    report = dict(base_schema=base, legal_schema=target, graph_schema=graph, listing_schema=listing,
        ktx=counts, total=total, categories=categories, indexed=indexed, source_before=before, source_after=after, base_unchanged=before == after,
        manifest_sha256=release_hash, activation='validated; apply docker-compose.ctu-ktx.yml')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ktx': counts, 'base_unchanged': before == after}), flush=True)
    engine.dispose()


if __name__ == '__main__':
    main()
