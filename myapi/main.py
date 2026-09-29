from fastapi import FastAPI,Request
from src.routers.service import router
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI()

app.include_router(router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    errors = exc.errors()

    field = errors[0]["loc"][-1]

    return JSONResponse(
        status_code=400,
        content={
            "message": f"Invalid field: {field}"
        }
    )