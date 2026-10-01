import os

from pathlib import Path

from fastapi import APIRouter, HTTPException
from openai import OpenAI, APITimeoutError

from src.llm.schema import ClassifyRequest, ClassifyResponse, Category, Urgency
from src.routers.parsing import load_prompt, parse_and_validate, quarantine_output, call_model

router = APIRouter()

@router.post("/classify", response_model = ClassifyResponse)

def classify(request: ClassifyRequest):

    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        return ClassifyResponse(
            category = Category.OTHER,
            urgency = Urgency.NORMAL,
            confidence = 0.0,
            reason = "The AI classification service is currently disabled."
        )

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
        api_key=os.environ["LLM_API_KEY"],
        timeout = 30.0,
        max_retries= 0
    )

    model = os.environ["LLM_MODEL"]

    try:
        raw_output = call_model(
            client,
            model,
            system_prompt,
            request.text
        )

    except APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail = "The model request timed out."
        )

    try:
        return parse_and_validate(raw_output)

    except Exception as error:
        repair_message = f"""
Your previous answer was rejected for this reason:

{error}

Your previous answer was :

{raw_output}

Your previous answer was rejected for this reason. Return only corrected JSON matching the schema.
"""

        try:
            repaired_output = call_model(
                client,
                model,
                system_prompt,
                repair_message,
                repair = True
            )

        except APITimeoutError:
            return HTTPException(
                status_code=504,
                detail = "The model repair request timed out."
            )

        try:
            return parse_and_validate(raw_output)

        except Exception as repair_error:
            quarantine_output(
                request.text,
                repaired_output,
                repair_error
            )

            raise HTTPException(
                status_code=422,
                detail= "The model could not produce a valid classification."
            )
