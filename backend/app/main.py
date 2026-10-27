"""FastAPI application: REST API + static frontend."""
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .graph import workflow
from .llm import LLMError
from .schemas import AnalyzeRequest, AnalyzeResponse

app = FastAPI(title="AI Job Description Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_input(text: str) -> str:
    """Return cleaned text or raise a friendly 400 error."""
    text = re.sub(r"[ \t]+", " ", (text or "")).strip()
    if not text:
        raise HTTPException(400, "Job description is empty. Please paste a job description.")
    if len(text) < config.MIN_JD_CHARS:
        raise HTTPException(
            400, f"Job description is too short (minimum {config.MIN_JD_CHARS} characters)."
        )
    if len(text) > config.MAX_JD_CHARS:
        raise HTTPException(400, f"Job description is too long (maximum {config.MAX_JD_CHARS} characters).")
    if not re.search(r"[A-Za-z]{3,}", text):
        raise HTTPException(400, "Invalid input. Please paste a readable job description in text form.")
    return text


@app.get("/api/health")
def health():
    return {"status": "ok", "model": config.GROQ_MODEL, "api_key_configured": bool(config.GROQ_API_KEY)}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest):
    text = _validate_input(payload.job_description)
    started = time.perf_counter()

    try:
        final_state = workflow.invoke({"job_description": text, "steps": []})
    except LLMError as exc:
        raise HTTPException(502, str(exc))
    except Exception as exc:  # unexpected failure
        raise HTTPException(500, f"Unexpected error while analysing the job description: {exc}")

    if final_state.get("error"):
        raise HTTPException(422, final_state["error"])

    return AnalyzeResponse(
        report=final_state["report"],
        steps=final_state["steps"],
        model=config.GROQ_MODEL,
        total_ms=int((time.perf_counter() - started) * 1000),
    )


# Serve the frontend (must be mounted last so /api routes keep priority)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
