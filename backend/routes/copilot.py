from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import CopilotRequest
from services.ai_copilot import process_copilot_query, SUGGESTED_QUESTIONS

router = APIRouter()


@router.post("/chat")
def chat(request: CopilotRequest, db: Session = Depends(get_db)):
    result = process_copilot_query(db, request.message, request.history or [])
    return result


@router.get("/suggestions")
def get_suggestions():
    return {"questions": SUGGESTED_QUESTIONS}
