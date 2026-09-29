import os

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.llm.schema import ClassifyRequest, ClassifyResponse, Category, Urgency

router = APIRouter()

@router.post("/classify", response_model = ClassifyResponse)
def classify(reqest: ClassifyRequest):
    if os.getenv("LLM_STUB") == "1":
        return ClassifyResponse(
            category=Category.OTHER,            #Test LLM call
            urgency=Urgency.NORMAL,
            confidence=0.5,
            reason="Stub response for testing."
        )

    return ClassifyResponse(
        category=Category.OTHER,
        urgency=Urgency.NORMAL,     #Real LLM call
        confidence=0.5,
        reason="LLM integration not enabled"
    )
