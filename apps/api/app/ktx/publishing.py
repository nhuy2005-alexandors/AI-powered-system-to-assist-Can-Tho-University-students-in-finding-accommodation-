"""Build real vectors before atomically switching the public catalogue."""
from __future__ import annotations

import hashlib
import json
import math

from sqlalchemy import text

from .catalog import fold_text, room_text


def catalogue_records(catalog):
    for room in catalog.room_types:
        yield dict(id=room.id,kind='room_type',source_id=room.source_id,content=room_text(room,catalog.academic_year),metadata=room.model_dump(mode='json'))
    for area in catalog.dormitories:
        p=area.location
        content=(f'KTX Đại học Cần Thơ {area.name}. {area.description} {area.buildings}. '
                 f'Khoảng {area.capacity} sinh viên. Tọa độ GPS: {p.lat}, {p.lng}. '
                 f'{p.label}; điểm đại diện, không phải tọa độ từng phòng hay cổng. Liên hệ {area.phone}.')
        yield dict(id='dormitory-'+area.id,kind='dormitory',source_id='intro',content=content,metadata=area.model_dump())
    for fact in catalog.facts:
        yield dict(id='fact-'+fact.id,kind='fact',source_id=fact.source_id,
                   content=fact.title+': '+fact.content,metadata=fact.model_dump())
    types={room.id:room for room in catalog.room_types}
    for room in catalog.rooms:
        content=f'KTX khu {room.dormitory_id}, dãy {room.building}, phòng {room.number}; loại {types[room.room_type_id].code}, sức chứa {room.capacity} người. {room.notes}'
        status={'unknown':'chưa xác nhận','available':'còn chỗ','full':'hết chỗ','maintenance':'bảo trì'}[room.status]
        content+=f' Ghi nhận thủ công: {status}; số chỗ trống {room.available_beds if room.available_beds is not None else "chưa biết"}; ngày {room.verified_at or "chưa ghi nhận"}. Không phải tồn phòng trực tiếp.'
        yield dict(id='inventory-'+room.id,kind='room_type',source_id=types[room.room_type_id].source_id,
                   content=content,metadata=room.model_dump(mode='json'))


def prepare_index(engine,catalog,embedder,model):
    entries=list(catalogue_records(catalog))
    if len({entry['id'] for entry in entries}) != len(entries):
        raise ValueError('Mã dữ liệu bị trùng với mã danh mục hệ thống')
    with engine.connect() as conn:
        old={row['id']:dict(row) for row in conn.execute(text(
            'SELECT id,kind,content_sha256,embedding_model,embedding_vector::text AS vector FROM ctu_ktx_search_documents'
        )).mappings()}
    pending=[]
    for entry in entries:
        entry['hash']=hashlib.sha256(entry['content'].encode()).hexdigest()
        prior=old.get(entry['id'])
        if prior and prior['kind']=='source_clause':
            raise ValueError('Mã danh mục trùng với điều khoản đã lưu')
        if prior and prior['content_sha256']==entry['hash'] and prior['embedding_model']==model:
            entry['vector']=prior['vector']
        else:
            pending.append(entry)
    for offset in range(0,len(pending),16):
        batch=pending[offset:offset+16]
        vectors=embedder.embed_passages([entry['content'] for entry in batch])
        if len(vectors)!=len(batch):
            raise ValueError('Không tạo đủ vector KTX')
        for entry,vector in zip(batch,vectors):
            if len(vector)!=384 or not all(math.isfinite(v) for v in vector) or not any(vector):
                raise ValueError('Vector KTX không hợp lệ')
            entry['vector']=json.dumps(vector)
    return entries,len(pending)


def publish_index(conn,catalog,entries,model):
    for entry in entries:
        conn.execute(text(
            'INSERT INTO ctu_ktx_search_documents(id,kind,source_id,content,normalized_content,metadata,content_sha256,embedding_vector,embedding_model) '
            'VALUES(:id,:kind,:source_id,:content,:normalized,CAST(:metadata AS jsonb),:hash,CAST(:vector AS vector),:model) '
            'ON CONFLICT(id) DO UPDATE SET kind=EXCLUDED.kind,source_id=EXCLUDED.source_id,content=EXCLUDED.content,'
            'normalized_content=EXCLUDED.normalized_content,metadata=EXCLUDED.metadata,content_sha256=EXCLUDED.content_sha256,'
            'embedding_vector=EXCLUDED.embedding_vector,embedding_model=EXCLUDED.embedding_model,embedded_at=now()'
        ),dict(entry,normalized=fold_text(entry['content']),metadata=json.dumps(entry['metadata'],ensure_ascii=False),model=model))
    # Preserve independently sourced CTU provisions, while removing superseded catalogue entries.
    conn.execute(text("DELETE FROM ctu_ktx_search_documents WHERE kind <> 'source_clause' AND NOT(id=ANY(:ids))"),
                 {'ids':[entry['id'] for entry in entries]})
    payload=json.dumps(catalog.model_dump(mode='json'),ensure_ascii=False,sort_keys=True)
    checksum=hashlib.sha256(payload.encode()).hexdigest()
    conn.execute(text(
        'INSERT INTO ctu_ktx_catalog(id,payload,content_sha256) VALUES(1,CAST(:payload AS jsonb),:hash) '
        'ON CONFLICT(id) DO UPDATE SET payload=EXCLUDED.payload,content_sha256=EXCLUDED.content_sha256,updated_at=now()'
    ),dict(payload=payload,hash=checksum))
    return checksum
