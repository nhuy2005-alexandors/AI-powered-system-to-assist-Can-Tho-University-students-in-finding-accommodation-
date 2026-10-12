"""Admin-only year drafts, publication, audit and public dormitory photographs."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID,uuid4

from fastapi import APIRouter,Depends,HTTPException,UploadFile,File
from fastapi.responses import FileResponse
from PIL import Image,ImageOps,UnidentifiedImageError
from pydantic import BaseModel,Field,model_validator,ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..auth import require_admin
from ..config import settings
from ..room_service.chatbot.router import get_service
from .catalog import KtxCatalog
from .publishing import prepare_index,publish_index

router=APIRouter(prefix='/admin/ktx',tags=['admin-ktx'])
public_media_router=APIRouter(prefix='/ktx/images',tags=['dormitories'])
log=logging.getLogger(__name__)
MAX_IMAGE=8*1024*1024


class YearCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    academic_year:str=Field(pattern=r'^20\d{2}-20\d{2}$')
    copy_from:int|None=Field(default=None,gt=0)
    @model_validator(mode='after')
    def consecutive(self):
        start,end=map(int,self.academic_year.split('-'))
        if end!=start+1:
            raise ValueError('Năm học phải gồm hai năm liên tiếp')
        return self


class YearSave(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:int=Field(ge=1)
    catalog:KtxCatalog

    @model_validator(mode='after')
    def consultation_fields(self):
        required={'fees','utilities','parking','wifi','security','quiet','registration','availability','contact'}
        if not required.issubset({fact.id for fact in self.catalog.facts}):
            raise ValueError('Thiếu thông tin tư vấn bắt buộc; hãy sửa nội dung thay vì xóa mục')
        for key in ('availability','contact'):
            if not any(key in fact.tags for fact in self.catalog.facts):
                raise ValueError('Cần giữ chủ đề '+key+' để chatbot tra cứu')
        if not {'intro','submitted','rules'}.issubset({source.id for source in self.catalog.sources}):
            raise ValueError('Cần giữ các nguồn gốc intro, submitted, rules')
        return self


class Revision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:int=Field(ge=1)


def get_year(conn,id,lock=False):
    row=conn.execute(text('SELECT * FROM ctu_ktx_years WHERE id=:id'+(' FOR UPDATE' if lock else '')),{'id':id}).mappings().first()
    if row is None:
        raise HTTPException(404,'Không tìm thấy năm học KTX')
    return dict(row)


def check_revision(row,revision):
    if row['revision']!=revision:
        raise HTTPException(409,'Dữ liệu đã được người khác cập nhật. Tải lại trước khi lưu.')


def audit(conn,actor,year_id,action,before,after):
    conn.execute(text('INSERT INTO ctu_ktx_admin_audit(year_id,actor_id,action,before_data,after_data) '
        'VALUES(:year,:actor,:action,CAST(:before AS jsonb),CAST(:after AS jsonb))'),dict(
            year=year_id,actor=actor,action=action,before=json.dumps(before,default=str,ensure_ascii=False),
            after=json.dumps(after,default=str,ensure_ascii=False)))


def summary(row):
    data=row['payload']
    return {key:row[key] for key in ('id','academic_year','revision','is_active','archived','updated_at','published_at')}|{
        'room_types':len(data.get('room_types',[])),'rooms':len(data.get('rooms',[])),'images':len(data.get('images',[])),
        'has_changes':row['published_payload'] is None or data!=row['published_payload']}


@router.get('/years')
def years(admin=Depends(require_admin),service=Depends(get_service)):
    with service.repo.engine.begin() as conn:
        # Also bootstrap installations whose catalogue was imported after DB initialization.
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('ctu-ktx-catalog'))"))
        conn.execute(text("INSERT INTO ctu_ktx_years(academic_year,payload,published_payload,is_active,published_at) "
            "SELECT '2026-2027',payload || '{\"academic_year\":\"2026-2027\"}'::jsonb, "
            "payload || '{\"academic_year\":\"2026-2027\"}'::jsonb,true,updated_at "
            "FROM ctu_ktx_catalog WHERE id=1 AND NOT EXISTS(SELECT 1 FROM ctu_ktx_years) "
            "ON CONFLICT(academic_year) DO NOTHING"))
        rows=conn.execute(text('SELECT * FROM ctu_ktx_years ORDER BY academic_year DESC')).mappings().all()
    return {'items':[summary(row) for row in rows]}


@router.post('/years',status_code=201)
def create_year(body:YearCreate,admin=Depends(require_admin),service=Depends(get_service)):
    try:
        with service.repo.engine.begin() as conn:
            template=get_year(conn,body.copy_from)['payload'] if body.copy_from else conn.execute(text(
                'SELECT payload FROM ctu_ktx_catalog WHERE id=1')).scalar_one_or_none()
            if template is None:
                raise HTTPException(409,'Chưa có danh mục gốc để sao chép')
            catalog=KtxCatalog.model_validate(template)
            catalog.academic_year=body.academic_year
            catalog.term=''
            for room in catalog.rooms:
                room.status='unknown'
                room.available_beds=None
                room.verified_at=None
            catalog.version='ktx-'+body.academic_year+'-draft'
            payload=catalog.model_dump(mode='json')
            id=conn.execute(text('INSERT INTO ctu_ktx_years(academic_year,payload,created_by,updated_by) '
                'VALUES(:year,CAST(:payload AS jsonb),:actor,:actor) RETURNING id'),dict(
                    year=body.academic_year,payload=json.dumps(payload,ensure_ascii=False),actor=admin.id)).scalar_one()
            row=get_year(conn,id)
            audit(conn,admin.id,id,'create',None,row)
        return summary(row)|{'catalog':payload}
    except IntegrityError:
        raise HTTPException(409,'Năm học này đã có. Mở lại hoặc khôi phục năm đang lưu trữ.')


@router.get('/years/{id}')
def read_year(id:int,admin=Depends(require_admin),service=Depends(get_service)):
    with service.repo.engine.connect() as conn:
        row=get_year(conn,id)
        logs=conn.execute(text('SELECT a.id,a.action,a.created_at,u.name AS actor_name '
            'FROM ctu_ktx_admin_audit a LEFT JOIN users u ON u.id=a.actor_id '
            'WHERE year_id=:id ORDER BY a.id DESC LIMIT 20'),{'id':id}).mappings().all()
    return summary(row)|{'catalog':KtxCatalog.model_validate(row['payload']).model_dump(mode='json'),
                         'audit':[dict(log) for log in logs]}


@router.put('/years/{id}')
def save_year(id:int,body:YearSave,admin=Depends(require_admin),service=Depends(get_service)):
    with service.repo.engine.begin() as conn:
        before=get_year(conn,id,True)
        check_revision(before,body.revision)
        if before['archived']:
            raise HTTPException(409,'Khôi phục năm học trước khi chỉnh sửa')
        if body.catalog.academic_year!=before['academic_year']:
            raise HTTPException(422,'Năm học của danh mục không khớp')
        conn.execute(text('UPDATE ctu_ktx_years SET payload=CAST(:data AS jsonb),revision=revision+1,'
            'updated_by=:actor,updated_at=now() WHERE id=:id'),dict(id=id,actor=admin.id,
                data=body.catalog.model_dump_json()))
        after=get_year(conn,id)
        audit(conn,admin.id,id,'save_draft',before,after)
    return summary(after)|{'catalog':after['payload']}


@router.post('/years/{id}/publish')
def publish_year(id:int,body:Revision,admin=Depends(require_admin),service=Depends(get_service)):
    with service.repo.engine.connect() as conn:
        row=get_year(conn,id)
    check_revision(row,body.revision)
    if row['archived']:
        raise HTTPException(409,'Không công bố năm đang lưu trữ')
    catalog=YearSave(revision=row['revision'],catalog=row['payload']).catalog
    with service.repo.engine.connect() as conn:
        preserved=set(conn.execute(text("SELECT DISTINCT source_id FROM ctu_ktx_search_documents WHERE kind='source_clause'")).scalars())
    if not preserved.issubset({source.id for source in catalog.sources}):
        raise HTTPException(422,'Cần giữ nguồn của các điều khoản CTU đã nhập')
    now=datetime.now(timezone.utc)
    catalog.version=f'ktx-{row["academic_year"]}-r{row["revision"]}-{now:%Y%m%d%H%M%S}'
    catalog.updated_at=now.date().isoformat()
    # A failed embedding leaves the public catalogue and draft intact.
    try:
        entries,new_vectors=prepare_index(service.repo.engine,catalog,service.embedder,settings.chatbot_embedding_model)
    except Exception:
        log.exception('Unable to prepare KTX publication')
        raise HTTPException(503,'Chưa cập nhật được dữ liệu chatbot. Bản nháp đã giữ; thử công bố lại sau.')
    with service.repo.engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('ctu-ktx-catalog'))"))
        before=get_year(conn,id,True)
        check_revision(before,body.revision)
        if before['archived']:
            raise HTTPException(409,'Năm học đã được lưu trữ trong lúc xử lý')
        checksum=publish_index(conn,catalog,entries,settings.chatbot_embedding_model)
        conn.execute(text('UPDATE ctu_ktx_years SET is_active=false WHERE is_active'))
        conn.execute(text('UPDATE ctu_ktx_years SET payload=CAST(:data AS jsonb),published_payload=CAST(:data AS jsonb),'
            'is_active=true,published_at=now(),updated_at=now(),updated_by=:actor,revision=revision+1 WHERE id=:id'),
            dict(id=id,data=catalog.model_dump_json(),actor=admin.id))
        after=get_year(conn,id)
        audit(conn,admin.id,id,'publish',before,after)
    return summary(after)|{'catalog':after['payload'],'index':{'sha256':checksum,'new_vectors':new_vectors,'records':len(entries)}}


@router.post('/years/{id}/archive')
def archive_year(id:int,body:Revision,admin=Depends(require_admin),service=Depends(get_service)):
    with service.repo.engine.begin() as conn:
        before=get_year(conn,id,True)
        check_revision(before,body.revision)
        if before['is_active']:
            raise HTTPException(409,'Công bố năm khác trước khi lưu trữ năm đang dùng')
        conn.execute(text('UPDATE ctu_ktx_years SET archived=NOT archived,revision=revision+1,updated_at=now(),'
            'updated_by=:actor WHERE id=:id'),dict(id=id,actor=admin.id))
        after=get_year(conn,id)
        audit(conn,admin.id,id,'restore' if before['archived'] else 'archive',before,after)
    return summary(after)|{'catalog':after['payload']}


def image_path(id:UUID):
    return Path(settings.media_dir)/'ktx'/f'{id}.jpg'


@router.post('/images',status_code=201)
def upload_image(file:UploadFile=File(...),admin=Depends(require_admin)):
    raw=file.file.read(MAX_IMAGE+1)
    if len(raw)>MAX_IMAGE:
        raise HTTPException(413,'Ảnh tối đa 8 MB')
    try:
        with Image.open(io.BytesIO(raw)) as original:
            if original.format not in {'JPEG','PNG','WEBP'} or original.width*original.height>24_000_000:
                raise ValueError()
            original.load()
            image=ImageOps.exif_transpose(original).convert('RGB')
            image.thumbnail((1920,1920))
            out=io.BytesIO()
            image.save(out,'JPEG',quality=85,optimize=True)
    except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError):
        raise HTTPException(422,'Chỉ nhận ảnh JPG, PNG hoặc WEBP hợp lệ, tối đa 24 megapixel')
    data=out.getvalue()
    id=uuid4()
    path=image_path(id)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    return dict(src=f'/api/ktx/images/{id}',original_url='',source_url='',credit='Ảnh do quản trị viên cung cấp',
                sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))


@public_media_router.get('/{id}')
def public_image(id:UUID):
    path=image_path(id)
    if not path.is_file():
        raise HTTPException(404,'Không tìm thấy ảnh KTX')
    return FileResponse(path,media_type='image/jpeg',headers={'Cache-Control':'public, max-age=86400','X-Content-Type-Options':'nosniff'})
