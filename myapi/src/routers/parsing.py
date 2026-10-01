import json
import random 
import time

from pathlib import Path
from src.llm.schema import ClassifyResponse
from openai import OpenAI, APITimeoutError

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "support-classifier-v1.md"
QUARANTINE_PATH = Path(__file__).resolve().parents[2] / "logs" / "quarantine.jsonl"
LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "llm_calls.jsonl"

def load_prompt():
    return PROMPT_PATH.read_text(encoding="utf-8")

def log_model_call(record):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

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

def call_model(client, model, system_prompt, user_content, repair = False):
    for attempt in range(3):
        start_time = time.perf_counter()
        try:
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

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000
            )

            usage = response.usage

            log_record = {
                "prompt_version" : "support-classifier-v1",
                "model" : model,
                "input_tokens" : usage.prompt_tokens if usage else 0,
                "output_tokens" : usage.completion_tokens if usage else 0,
                "duration_ms" : duration_ms,
                "repair" : repair
            }

            log_model_call(log_record)

            return response.choices[0].message.content

        except Exception as error:
            #Retry only on the errors that is considered temporary.
            status_code = getattr(error, "status_code", None)

            is_timeout = isinstance(error, APITimeoutError)
            is_rate_limit = status_code == 429
            is_server_error = (
                status_code is not None
                and 500 <= status_code <= 599
            )

            should_retry = (
                is_timeout
                or is_rate_limit
                or is_server_error
            )

            if not should_retry or attempt == 2:
                raise

            retry_after = None

            if status_code == 429:
                retry_after = getattr(error, "headers", {}).get("retry-after")

            if retry_after is not None:
                delay = float(retry_after)
            else:
                delay = (2 ** attempt) + random.uniform(0, 0.5)

            time.sleep(delay)