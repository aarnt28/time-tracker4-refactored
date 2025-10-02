from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.hardware import HardwareCreate, HardwareUpdate, HardwareOut
from ..crud.hardware import list_hardware, get_hardware, create_hardware, update_hardware, delete_hardware
from ..deps.auth import require_ui_or_token

router = APIRouter(prefix="/api/v1/hardware", tags=["hardware"])


@router.get("", response_model=list[HardwareOut], dependencies=[Depends(require_ui_or_token)])
def api_list(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    return list_hardware(db, limit=limit, offset=offset)


@router.get("/{item_id}", response_model=HardwareOut, dependencies=[Depends(require_ui_or_token)])
def api_get(item_id: int, db: Session = Depends(get_db)):
    r = get_hardware(db, item_id)
    if not r:
        raise HTTPException(404, "Not found")
    return r


@router.post("", response_model=HardwareOut, dependencies=[Depends(require_ui_or_token)])
def api_create(payload: HardwareCreate, db: Session = Depends(get_db)):
    try:
        return create_hardware(db, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{item_id}", response_model=HardwareOut, dependencies=[Depends(require_ui_or_token)])
def api_update(item_id: int, payload: HardwareUpdate, db: Session = Depends(get_db)):
    r = get_hardware(db, item_id)
    if not r:
        raise HTTPException(404, "Not found")
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        return r
    return update_hardware(db, r, data)


@router.delete("/{item_id}", dependencies=[Depends(require_ui_or_token)])
def api_delete(item_id: int, db: Session = Depends(get_db)):
    r = get_hardware(db, item_id)
    if not r:
        raise HTTPException(404, "Not found")
    delete_hardware(db, r)
    return {"status": "deleted"}