
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

ALLOWED_ORIGIN = "https://dash-rg3ljf.example.com"
EMAIL = os.environ.get("EMAIL", "YOUR_LOGGED_IN_EMAIL")

# Strict CORS policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Add required headers to every response
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = str(uuid.uuid4())

        response = await call_next(request)

        duration = time.perf_counter() - start
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration:.6f}"

        return response

app.add_middleware(MetricsMiddleware)


@app.get("/stats")
def get_stats(values: str):
    try:
        numbers = [int(value.strip()) for value in values.split(",")]
        if not numbers:
            raise ValueError("At least one integer is required")
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": "values must be comma-separated integers"},
        )

    return {
        "email": EMAIL,
        "count": len(numbers),
        "sum": sum(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers),
    }
