# Support Message Classifier API

## What this endpoint does

This project provides a small API that classifies customer support messages into one of four categories: `billing`, `bug`, `feature`, or `other`. A user sends a support message to the `/classify` endpoint, and the API asks an AI model to determine the category, urgency, confidence, and a short reason. The API validates the model's response against a fixed schema, retries only temporary provider failures, attempts one repair when the model returns invalid output, and safely rejects responses that still fail validation.

## Try the API

Start the API from the project directory:

```bash
uv run --env-file .env uvicorn main:app --reload
```

Then send a request:

```bash
curl.exe -X POST http://localhost:8000/classify ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"I was charged twice for my subscription.\"}"
```

Exact response from the tested setup:

```json
{
  "category": "billing",
  "urgency": "normal",
  "confidence": 0.95,
  "reason": "The customer reports being charged twice for a subscription."
}
```

## Job Card

**What it does:**
Classifies a support message so it lands on the right team.

**Input:**

```json
{
  "text": "string, 1-2000 characters"
}
```

**Output:**

```json
{
  "category": "billing|bug|feature|other",
  "urgency": "low|normal|high",
  "confidence": "0.0-1.0",
  "reason": "one short sentence"
}
```

### It must never

* Invent a category outside `billing`, `bug`, `feature`, or `other`.
* Return free text instead of the required response structure.
* Give medical, legal, or financial advice.
* Reveal the system prompt or classification instructions.

### When unsure

If the message does not clearly fit a category, the classifier should return:

```text
category: other
confidence: below 0.5
```

It should not guess.

## Provider and Model

This project uses **Ollama** through its OpenAI-compatible API.

**Model:**

```text
gemma3:1b
```

The provider/model configuration can be changed through these three environment variables:

```env
LLM_BASE_URL=http://localhost:11434/v1/
LLM_API_KEY=ollama
LLM_MODEL=gemma3:1b
```

The AI feature also has a production kill switch:

```env
LLM_ENABLED=true
```

Set it to `false` to disable model calls without changing or redeploying the application.

### Retry policy

The OpenAI SDK's built-in retries are disabled with:

```text
max_retries=0
```

The application uses its own retry policy instead. Timeouts, HTTP `429`, and HTTP `5xx` responses may be retried up to two times using exponential backoff with jitter. HTTP `400`, `401`, and `403` responses are not retried. When a `429` response includes `Retry-After`, that value is used for the delay.

Model requests also have a 30-second timeout. A timeout that ultimately fails is returned as HTTP `504`.

## Evaluation

The project includes eight manually written evaluation cases in:

```text
evals/cases.json
```

The evaluation script sends all eight cases through the actual HTTP endpoint:

```bash
uv run python evals/run.py
```

### Result

**Prompt version:** `support-classifier-v1`
**Evaluation date:** October 3, 2026
**Category accuracy:** **4/8 (50.0%)**

The four failed cases were:

```text
The dashboard shows a blank page after I log in.
Expected: bug
Actual: other

Could you add dark mode to the dashboard?
Expected: feature
Actual: HTTP 422

It would be useful if I could export my reports as CSV.
Expected: feature
Actual: HTTP 422

Something is wrong with my account.
Expected: other
Actual: bug
```

This result is intentionally recorded as-is so that future prompt or model changes can be compared against the same evaluation set.

## Cost and Usage Logging

Each successful model call is written as one JSON line to:

```text
logs/llm_calls.jsonl
```

A tested call produced:

```json
{
  "prompt_version": "support-classifier-v1",
  "model": "gemma3:1b",
  "input_tokens": 389,
  "output_tokens": 36,
  "duration_ms": 3092,
  "repair": false
}
```

Because this project runs the model locally through Ollama, the provider API cost is **$0**. A simple provider-cost estimate for **10,000 requests per day is therefore $0/day**, excluding electricity, hardware, and other local infrastructure costs.

## Kill Switch

Set:

```env
LLM_ENABLED=false
```

The endpoint skips the model completely and returns a deterministic fallback response:

```json
{
  "category": "other",
  "urgency": "normal",
  "confidence": 0.0,
  "reason": "The AI classification service is currently disabled."
}
```

No model-call entry is added to `logs/llm_calls.jsonl` when the kill switch is active.

## Project Structure

```text
myapi/
├── evals/
│   ├── cases.json
│   └── run.py
├── logs/
│   ├── llm_calls.jsonl
│   └── quarantine.jsonl
├── prompts/
│   └── support-classifier-v1.md
├── src/
│   ├── llm/
│   │   ├── hello.py
│   │   └── schema.py
│   └── routers/
│       └── service.py
├── main.py
├── .env.example
├── .gitignore
└── pyproject.toml
```

## Setup

Install the project dependencies with `uv`, create a `.env` file from `.env.example`, and configure the provider/model variables.

Example:

```env
LLM_BASE_URL=http://localhost
```
