"""Bilgi Merkezi yönetim uçları; yalnızca yönetici rolü erişir."""
from __future__ import annotations

import hashlib
import logging
from typing import Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

import app_log
import kb_service as service
import rag_provider
from admin_api import require_admin
from database.connection import DatabaseError, connect

router = APIRouter(prefix="/admin/kb", tags=["Bilgi Merkezi"])
logger = logging.getLogger(__name__)
Domain = Literal["general_it", "windows_server", "oracle_db"]


class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["tickets_csv", "guide_json"]
    filename: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=service.MAX_CONTENT_CHARS)
    domain: Domain = "general_it"
    license_note: str = Field(default="", max_length=200)
    dry_run: bool = True


class PreviewItem(BaseModel):
    id: str
    domain: str
    title: str
    problem: str


class UploadResult(BaseModel):
    dry_run: bool
    kind: str
    valid: int
    errors: list[str]
    preview: list[PreviewItem]
    added: int = 0
    already_present: int = 0


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[UUID] = Field(min_length=1, max_length=10)


class ApproveItem(BaseModel):
    id: UUID
    status: Literal["indexed", "already", "failed"]
    message: str = ""


class ApproveResult(BaseModel):
    items: list[ApproveItem]


class StatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    excluded: bool


class GroupCount(BaseModel):
    record_type: str
    domain: str
    review_status: str
    count: int


class Summary(BaseModel):
    groups: list[GroupCount]
    total: int
    searchable: int
    chunks: int


class RecordInfo(BaseModel):
    id: UUID
    source_record_id: str
    record_type: str
    domain: str
    title: str
    review_status: str
    index_status: str
    source_name: str
    license: str
    problem: str


class RecordPage(BaseModel):
    items: list[RecordInfo]
    total: int
    next_offset: int | None


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Bilgi tabanına şu anda ulaşılamıyor.")


@router.get("/summary", response_model=Summary)
def get_summary(admin: dict = Depends(require_admin)):
    try:
        with connect() as connection:
            return service.summary(connection)
    except (DatabaseError, psycopg.Error):
        raise _unavailable() from None


@router.get("/records", response_model=RecordPage)
def get_records(review_status: Literal["pending", "approved", "excluded"] | None = None,
                domain: Domain | None = None,
                record_type: Literal["ticket", "qa", "documentation"] | None = None,
                q: str | None = Query(default=None, max_length=100),
                offset: int = Query(default=0, ge=0, le=1_000_000),
                limit: int = Query(default=50, ge=1, le=100), admin: dict = Depends(require_admin)):
    try:
        with connect() as connection:
            return service.list_records(connection, review_status=review_status, domain=domain,
                                        record_type=record_type, query=q, offset=offset, limit=limit)
    except (DatabaseError, psycopg.Error):
        raise _unavailable() from None
    except service.KnowledgeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.post("/upload", response_model=UploadResult)
def upload(request: UploadRequest, admin: dict = Depends(require_admin)):
    """Dosyayı doğrular; ``dry_run=false`` ise kayıtları ``pending`` olarak ekler (embedding üretmez)."""
    digest = hashlib.sha256(request.content.encode("utf-8")).hexdigest()
    try:
        if request.kind == "tickets_csv":
            if not request.license_note.strip():
                raise service.KnowledgeError("Kaynak veya lisans notu zorunlu.")
            records, errors = service.parse_tickets_csv(request.content, request.domain)
        else:
            records, errors = service.parse_guides_json(request.content)
    except service.KnowledgeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    result = {"dry_run": request.dry_run, "kind": request.kind, "valid": len(records),
              "errors": errors[:20], "preview": service.preview_items(request.kind, records, request.domain)}
    if request.dry_run:
        return result
    if errors or not records:
        raise HTTPException(status_code=422, detail="Dosyada hatalar var; düzeltip yeniden yükleyin.\n"
                            + "\n".join(errors[:10]))
    try:
        with connect() as connection:
            if request.kind == "tickets_csv":
                counts = service.stage_tickets(connection, records, domain=request.domain,
                                               filename=request.filename, license_note=request.license_note.strip(),
                                               file_digest=digest)
            else:
                counts = service.stage_guides(connection, records, filename=request.filename, file_digest=digest)
    except service.KnowledgeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except (DatabaseError, psycopg.Error):
        raise _unavailable() from None
    app_log.log_event("info", "kb.upload_staged", user_id=str(admin["id"]), details={
        "kind": request.kind, "filename": request.filename, "domain": request.domain, **counts})
    return {**result, **counts}


@router.post("/approve", response_model=ApproveResult)
def approve(request: ApproveRequest, admin: dict = Depends(require_admin)):
    """Her kayıt kendi transaction'ında embedding'lenir; biri başarısız olursa diğerleri etkilenmez."""
    items = []
    for record_id in dict.fromkeys(request.ids):
        try:
            with connect() as connection:
                outcome = service.approve_record(connection, str(record_id), rag_provider.embed_question)
            items.append({"id": record_id, **outcome})
        except service.KnowledgeError as error:
            items.append({"id": record_id, "status": "failed", "message": str(error)})
        except rag_provider.ServiceUnavailable as error:
            items.append({"id": record_id, "status": "failed", "message": str(error)})
        except (DatabaseError, psycopg.Error):
            raise _unavailable() from None
        except Exception as error:
            # Ham servis yanıtı veya bağlantı ayrıntısı sızdırma.
            logger.error("Kayıt indekslenemedi: %s", type(error).__name__)
            items.append({"id": record_id, "status": "failed", "message": "Embedding üretilemedi; tekrar deneyin."})
    counts = {name: sum(1 for item in items if item["status"] == name) for name in ("indexed", "already", "failed")}
    app_log.log_event("warning" if counts["failed"] else "info", "kb.approve", user_id=str(admin["id"]),
                      details={"record_ids": [str(i) for i in dict.fromkeys(request.ids)], **counts})
    return {"items": items}


@router.post("/records/{record_id}/status")
def set_status(record_id: UUID, request: StatusRequest, admin: dict = Depends(require_admin)):
    try:
        with connect() as connection:
            result = service.exclude_record(connection, str(record_id), request.excluded)
        app_log.log_event("info", "kb.exclude" if request.excluded else "kb.restore", user_id=str(admin["id"]),
                          details={"record_id": str(record_id), "status": result["status"]})
        return result
    except service.KnowledgeError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (DatabaseError, psycopg.Error):
        raise _unavailable() from None
