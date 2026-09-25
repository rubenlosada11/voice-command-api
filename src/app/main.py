import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.app.core.config import get_settings
from src.app.api.routes.instruction import router as instruction_router
from src.app.api.routes.tasks import router as tasks_router
from src.app.api.routes.transcribe import router as transcribe_router
from src.app.services.groq_client import GroqServiceError
from src.app.services.instruction_resolver import InvalidInstructionError
from src.app.services.speech_to_text import EmptyTranscriptionError
from src.app.services.task_store import TaskNotFoundError


async def handle_task_not_found(_: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


async def handle_empty_transcription(
    _: Request, exc: EmptyTranscriptionError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


async def handle_upstream_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(exc)},
    )


def create_app() -> FastAPI:
    # Uvicorn only configures its own loggers; this makes the app's INFO logs visible too.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
    settings = get_settings()
    app = FastAPI(
        title="Voice Command Transcription API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    app.add_exception_handler(TaskNotFoundError, handle_task_not_found)
    app.add_exception_handler(EmptyTranscriptionError, handle_empty_transcription)
    app.add_exception_handler(GroqServiceError, handle_upstream_error)
    app.add_exception_handler(InvalidInstructionError, handle_upstream_error)

    app.include_router(tasks_router)
    app.include_router(instruction_router)
    app.include_router(transcribe_router)
    return app


app = create_app()
