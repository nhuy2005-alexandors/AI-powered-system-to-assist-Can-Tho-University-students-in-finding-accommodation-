"""Fail closed: this evaluation may send only public legal corpus to Gemini."""
from sqlalchemy import text
from app.room_service.chatbot.parser import parse_query
from app.room_service.chatbot.topics import TOPICS


def assert_legal_cases(cases):
    if not cases or any(c['category']=='find_listing' or parse_query(c['question']).intent!='legal_question' for c in cases):
        raise ValueError('Legal-only evaluation rejects listing/non-legal questions')


def install(service, engine, cases, schema):
    assert_legal_cases(cases)
    allowed_questions={c['question'] for c in cases}
    with engine.connect() as conn:
        pairs=set(conn.execute(text(f'SELECT document_id,id FROM {schema}.legal_chunks')).tuples())
    if not pairs: raise ValueError('Empty public legal corpus')
    def check(rows):
        for row in rows:
            if (row.get('document_id'),row.get('chunk_id')) not in pairs or row.get('category') not in TOPICS:
                raise ValueError('Cloud boundary rejects evidence outside the legal corpus')
            if any(key in row for key in ('listing_id','parsed_amenities','address','phone','price','catalog_record')):
                raise ValueError('Cloud boundary rejects listing fields')
    def denied(*args,**kwargs):
        raise ValueError('Housing retrieval disabled in legal-only evaluation')
    service.repo.retrieve=denied
    original_legal=service.repo.retrieve_legal
    def legal(*args,**kwargs):
        rows=original_legal(*args,**kwargs)
        check(rows)
        return rows
    service.repo.retrieve_legal=legal
    original_ask=service.ask
    def ask(body):
        if body.message not in allowed_questions or body.conversation_history or body.conversation_state:
            raise ValueError('Only approved public legal bank questions are allowed')
        if parse_query(body.message).intent!='legal_question':
            raise ValueError('Non-legal route blocked before provider call')
        return original_ask(body)
    service.ask=ask
    writer=getattr(service.generator,'writer',None)
    if writer is not None:
        original_write=writer.synthesize
        def write(question,draft,*args,**kwargs):
            check(draft.selected_evidence)
            return original_write(question,draft,*args,**kwargs)
        writer.synthesize=write
    verifier=getattr(service.generator,'verifier',None)
    if verifier is not None:
        original_check=verifier.check_legal_evidence
        def verify(question,answer,contexts,*args,**kwargs):
            check(contexts)
            return original_check(question,answer,contexts,*args,**kwargs)
        verifier.check_legal_evidence=verify
    return dict(legal_only=True,approved_questions=len(cases),legal_source_pairs=len(pairs),
        listing_retrieval_disabled=True,cloud_evidence_checked_before_each_call=True,
        policy='Public legal questions and legal corpus only; no listing context or housing catalog is permitted at the cloud boundary.')
