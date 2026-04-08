from __future__ import annotations


from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class FeedbackRequest(BaseModel):
    session_id: str
    query_id: int
    helpful: bool
    comment: str = ""


class FeedbackResponse(BaseModel):
    status: str
    message: str


# Logger is injected at startup via set_logger
_logger = None


def set_logger(logger) -> None:
    global _logger
    _logger = logger


@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest) -> FeedbackResponse:
    if _logger is None:
        raise HTTPException(status_code=503, detail="Logger not initialized")

    try:
        _logger.log_feedback(
            session_id=feedback.session_id,
            query_id=feedback.query_id,
            helpful=feedback.helpful,
            comment=feedback.comment,
        )
        return FeedbackResponse(status="ok", message="Feedback recorded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {e}")
