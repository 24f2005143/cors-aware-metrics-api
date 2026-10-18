
import os
import time
import uuid
import secrets
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

EMAIL = os.environ.get("EMAIL", "YOUR_LOGGED_IN_EMAIL")
API_KEY = os.environ.get(
    "ANALYTICS_API_KEY",
    "ak_ggya7kimi7nhbligtlvbmjoy"
)

STATS_ORIGIN = "https://dash-rg3ljf.example.com"


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    start = time.perf_counter()
    request_id = str(uuid.uuid4())
    origin = request.headers.get("origin", "")
    path = request.url.path

    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        if path == "/stats":
            allowed = origin == STATS_ORIGIN
        elif path == "/analytics":
            allowed = True
        else:
            allowed = False

        if not allowed:
            response = Response(status_code=400)
        else:
            response = Response(status_code=200)

        if allowed:
            response.headers["Access-Control-Allow-Origin"] = (
                STATS_ORIGIN if path == "/stats" else "*"
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, OPTIONS" if path == "/stats"
                else "POST, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "*" if path == "/stats"
                else "Content-Type, X-API-Key"
            )
            response.headers["Access-Control-Max-Age"] = "600"

    else:
        response = await call_next(request)

        if path == "/stats" and origin == STATS_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = STATS_ORIGIN
        elif path == "/analytics":
            response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = (
        f"{max(0, time.perf_counter() - start):.6f}"
    )
    return response


@app.get("/stats")
def get_stats(values: str):
    try:
        numbers = [int(v.strip()) for v in values.split(",")]
        if not numbers:
            raise ValueError()
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


@app.post("/analytics")
async def analytics(request: Request):
    supplied_key = request.headers.get("X-API-Key", "")

    if not secrets.compare_digest(supplied_key, API_KEY):
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"},
        )

    try:
        body = await request.json()
        events = body["events"]

        if not isinstance(events, list):
            raise ValueError()

        for event in events:
            if (
                not isinstance(event, dict)
                or not isinstance(event.get("user"), str)
                or isinstance(event.get("amount"), bool)
                or not isinstance(event.get("amount"), (int, float))
            ):
                raise ValueError()

    except (ValueError, KeyError, TypeError):
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid events payload"},
        )

    user_totals = defaultdict(float)
    revenue = 0.0

    for event in events:
        amount = event["amount"]
        if amount > 0:
            revenue += amount
            user_totals[event["user"]] += amount

    top_user = (
        max(user_totals, key=user_totals.get)
        if user_totals else ""
    )

    return {
        "email": EMAIL,
        "total_events": len(events),
        "unique_users": len({e["user"] for e in events}),
        "revenue": revenue,
        "top_user": top_user,
    }
