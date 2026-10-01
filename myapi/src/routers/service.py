import os

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import OpenAI

from src.llm.schema import ClassifyRequest, ClassifyResponse, Category, Urgency

router = APIRouter()

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "support-classifier-v1.md"

def load_prompt():
    return PROMPT_PATH.read_text(encoding="utf-8")

@router.post("/classify")
def classify(request: ClassifyRequest):

    if os.getenv("LLM_STUB") == "1":
        return {
            "category": "other",            #Test LLM call
            "urgency": "normal",
            "confidence": 0.5,
            "reason": "Stub response for testing."
        }

    system_prompt = load_prompt()

    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"]
    )

    response = client.chat.completions.create(
        model = os.environ["LLM_MODEL"],
        messages = [
            {
                "role" : "system",
                "content" : system_prompt
            },
            {
                "role" : "user",
                "content" : request.text
            }
        ],
        temperature=0
    )

    return {
        "response" : response.choices[0].message.content
    }

    return ClassifyResponse(
        category=Category.OTHER,
        urgency=Urgency.NORMAL,     #Real LLM call
        confidence=0.5,
        reason="LLM integration not enabled"
    )
