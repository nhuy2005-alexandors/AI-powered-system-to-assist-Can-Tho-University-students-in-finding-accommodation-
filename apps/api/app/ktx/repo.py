from __future__ import annotations

from sqlalchemy import text

from .catalog import KtxCatalog, fold_text


class KtxRepository:
    def __init__(self, engine):
        self.engine = engine

    def available(self) -> bool:
        with self.engine.connect() as conn:
            return bool(conn.execute(text("SELECT to_regclass('public.ctu_ktx_catalog')")).scalar())

    def catalog(self) -> KtxCatalog | None:
        with self.engine.connect() as conn:
            data = conn.execute(text("SELECT payload FROM public.ctu_ktx_catalog WHERE id=1")).scalar_one_or_none()
            if data and not data.get('academic_year') and conn.execute(text("SELECT to_regclass('public.ctu_ktx_years')")).scalar():
                year=conn.execute(text('SELECT academic_year FROM ctu_ktx_years WHERE is_active')).scalar_one_or_none()
                if year:
                    data=dict(data,academic_year=year)
        return KtxCatalog.model_validate(data) if data else None

    def search(self, query, vector, *, kinds=None, source_ids=None, max_chars=None, limit=5):
        clauses = ["kind = ANY(:kinds)"] if kinds else ["true"]
        params = dict(kinds=kinds, query=fold_text(query), limit=min(limit, 10))
        if source_ids:
            clauses.append("source_id = ANY(:source_ids)")
            params["source_ids"] = source_ids
        if max_chars:
            clauses.append("length(content) <= :max_chars")
            params["max_chars"] = max_chars
        phrases = ("qua dem", "nguoi ngoai", "phu huynh", "nguoi than", "tiep khach", "nau an",
                   "hut thuoc", "ruou bia", "ve sinh", "gui xe", "gio nghi", "gio ra vao", "chua chay")
        bonuses = []
        for phrase in phrases:
            if phrase in params["query"]:
                key = "phrase_" + str(len(bonuses))
                params[key] = "%" + phrase + "%"
                bonuses.append("CASE WHEN normalized_content LIKE :" + key + " THEN 0.6 ELSE 0 END")
        boost = " + " + " + ".join(bonuses) if bonuses else ""
        semantic = "0.0"
        if vector is not None:
            params["vector"] = "[" + ",".join(str(float(v)) for v in vector) + "]"
            semantic = "(1 - (embedding_vector <=> CAST(:vector AS vector)))"
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id,kind,source_id,content,metadata," + semantic + " AS vector_score "
                "FROM public.ctu_ktx_search_documents WHERE " + " AND ".join(clauses) +
                " ORDER BY (" + semantic +
                " + ts_rank(to_tsvector('simple',normalized_content),plainto_tsquery('simple',:query))" + boost + ") DESC, id LIMIT :limit"
            ), params).mappings().all()
        return [dict(row) for row in rows]
