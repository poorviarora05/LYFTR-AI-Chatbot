import os
import time
import logging

from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field, field_validator

from database import (
    init_db,
    get_messages,
    get_system_prompt,
    save_exchange,
    session_exists,
    check_database
)

from llm_service import (
    generate_response,
    get_key_count,
    DEFAULT_SYSTEM_PROMPT,
    AllProvidersUnavailable
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize database on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized successfully")
    yield


# Create FastAPI application
app = FastAPI(
    title="LYFTR AI Chatbot",
    description="LLM Chatbot with Key Failover and Response Caching",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)


# Configure CORS
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Simulate-Failure"]
)


# Request validation
class ChatRequest(BaseModel):

    session_id: str = Field(
        min_length=1,
        max_length=128
    )

    message: str = Field(
        min_length=1,
        max_length=4000
    )

    system_prompt: Optional[str] = None

    @field_validator("session_id", "message", mode="before")
    @classmethod
    def validate_text(cls, value):

        if not isinstance(value, str):
            raise ValueError("Value must be a string")

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty")

        return value


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    logger.error(
        "Unexpected error: %s",
        type(exc).__name__
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error"
        }
    )


# ENDPOINT 1: Health Check
@app.get("/health")
def health():

    try:
        check_database()

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="database unavailable"
        )

    if get_key_count() < 2:
        raise HTTPException(
            status_code=503,
            detail="at least two API keys are required"
        )

    return {
        "status": "ok",
        "keys_configured": get_key_count(),
        "cache_enabled": True
    }


# ENDPOINT 2: Chat
@app.post("/chat")
def chat(
    request: ChatRequest,
    x_simulate_failure: Optional[str] = Header(
        default=None,
        alias="X-Simulate-Failure"
    )
):

    start_time = time.perf_counter()

    session_id = request.session_id
    user_message = request.message

    # Retrieve existing conversation
    history = get_messages(session_id)

    # Retrieve session system prompt
    saved_prompt = get_system_prompt(session_id)

    if request.system_prompt is not None:
        system_prompt = request.system_prompt
    elif saved_prompt is not None:
        system_prompt = saved_prompt
    else:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    # Prepare full conversation for the LLM
    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # Add previous messages
    for item in history:

        messages.append({
            "role": item["role"],
            "content": item["content"]
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    try:

        # Generate AI response
        result = generate_response(
            messages=messages,
            failure_header=x_simulate_failure
        )

    except AllProvidersUnavailable:

        raise HTTPException(
            status_code=503,
            detail="all providers unavailable"
        )

    reply = result["reply"]
    metadata = result["metadata"]

    # Measure total processing latency
    metadata["latency_ms"] = int(
        (time.perf_counter() - start_time) * 1000
    )

    # Save only successful conversations
    save_exchange(
        session_id=session_id,
        system_prompt=system_prompt,
        user_message=user_message,
        assistant_reply=reply,
        metadata=metadata
    )

    return {
        "session_id": session_id,
        "reply": reply,
        "metadata": metadata
    }


# ENDPOINT 3: Session History
@app.get("/sessions/{session_id}/messages")
def session_history(session_id: str):

    if not session_exists(session_id):

        raise HTTPException(
            status_code=404,
            detail="session not found"
        )

    return {
        "session_id": session_id,
        "messages": get_messages(session_id)
    }