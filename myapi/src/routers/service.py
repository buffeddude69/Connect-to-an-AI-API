import os
import json

from pathlib import Path

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from src.llm.schema import ClassifyRequest, ClassifyResponse, Category, Urgency

router = APIRouter()

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "support-classifier-v1.md"
QUARANTINE_PATH = Path(__file__).resolve().parents[2] / "logs" / "quarantine.jsonl"

def load_prompt():
    return PROMPT_PATH.read_text(encoding="utf-8")

def parse_model_output(raw_output : str):
    cleaned = raw_output.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    #Find JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Model output does not contain a JSON object.")

    json_text = cleaned[start : end + 1]

    return json.loads(json_text)

def parse_and_validate(raw_output : str) -> ClassifyResponse:
    parsed = parse_model_output(raw_output)

    return ClassifyResponse.model_validate(parsed)

def quarantine_output(input_text, raw_output, error):
    QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "input" : input_text,
        "error": str(error),
        "prompt_version": "support-classifier-v1",
        "raw_output" : raw_output,
    }

    with QUARANTINE_PATH.open("a", encoding = "utf-8") as file:
        file.write(json.dumps(record) + "\n")

def call_model(client, model, system_prompt, user_content):
    response = client.chat.completions.create(
        model = model,
        messages = [
            {
                "role" : "system",
                "content" : system_prompt
            },
            {
                "role" : "user",
                "content" : user_content
            }
        ],
        temperature = 0
    )

    return response.choices[0].message.content

@router.post("/classify", response_model = ClassifyResponse)

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

    model = os.environ["LLM_MODEL"]

    raw_output = call_model(
        client,
        model,
        system_prompt,
        request.text
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

        repaired_output = call_model(
            client,
            model,
            system_prompt,
            repair_message
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
