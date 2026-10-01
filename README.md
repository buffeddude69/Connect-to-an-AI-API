### Connect-to-an-AI-API
FlyRank Assignment

Integrate an LLM to an API

## 1. Tech Stack
 - Python FastAPI
 - Ollama gemm3:1b Model

# Stage 0:

Used ollama specifically gemma3:1b for the LLM model.
Sucessfully connected the python application to the LLM.

# Stage 2:

## Prompt Specification

Model behavior testing without its resrictions

# Results
- billing message produced the expected JSON classification.
- Bug message was classified but the model wrapped the JSON in a Markdown code fence.
- Feature message did not follow the classification format and returned a refusal-style response.
- These inconsistencies will need to be handles in a later stage with structured output/validation.

# Stage 3
- Parsed raw model output
- Handled identified unnecessary output
- Validated the expected output with a schema
- Reject invalid enum values
- Return schema-shape JSON output on success
- Don't return raw text
- Repaire exactly once
- Will quarantine on failed second attempt
- Return 422 after second failure


