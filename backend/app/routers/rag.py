import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.dependencies import get_db, get_current_user
from app.models.scan import Scan
from app.models.user import User
from app.services.rag_service import get_disposal_advice

router = APIRouter()


class RAGQueryRequest(BaseModel):
    scan_id: UUID
    follow_up_question: Optional[str] = None


class RAGFeedback(BaseModel):
    scan_id: UUID
    helpful: bool
    comment: Optional[str] = None


@router.post("/query")
async def rag_query(
    body: RAGQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = db.query(Scan).filter(Scan.id == body.scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    class_names = []
    if scan.detected_classes:
        class_names = [d["class_name"] for d in scan.detected_classes]

    question = body.follow_up_question or (
        "What is the best way to dispose of " + ", ".join(class_names) + "?"
    )

    city = current_user.city or "India"
    if body.follow_up_question:
        # Use previous RAG response as context
        context_prefix = f"[Previous detection: {', '.join(class_names)}] "
        question = context_prefix + body.follow_up_question

    async def stream_response():
        from starlette.concurrency import run_in_threadpool
        advice, sources = await run_in_threadpool(get_disposal_advice, class_names, city)
        # Stream word by word for SSE effect
        for word in advice.split(" "):
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
        # Send sources at end
        yield f"data: {json.dumps({'sources': sources, 'done': True})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{scan_id}")
def rag_history(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        "scan_id": scan_id,
        "rag_response": scan.rag_response,
        "rag_sources": scan.rag_sources,
    }
