import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from src.app.schemas.voice import InstructionRequest, TranscribeFlowResponse
from src.app.services.instruction_executor import execute_instruction
from src.app.services.instruction_resolver import resolve_instruction
from src.app.services.speech_to_text import transcribe_audio
from src.app.utils.language import normalize_transcription_language

logger = logging.getLogger(__name__)
router = APIRouter(tags=["transcribe"])

SUPPORTED_AUDIO_EXTENSIONS = {"flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "ogg", "wav", "webm"}
MAX_AUDIO_BYTES = 25 * 1024 * 1024


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("application/json"):
        transcription = await _read_manual_transcription(request)
    elif content_type.startswith("multipart/form-data"):
        transcription = await _transcribe_upload(request)
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Send multipart/form-data with an audio 'file' or JSON with 'transcription'.",
        )

    logger.info("Transcription: %r", transcription)
    instruction = await resolve_instruction(transcription)
    logger.info(
        "Instruction: %s %s %s", instruction.method, instruction.endpoint, instruction.params
    )
    result = execute_instruction(instruction)
    return TranscribeFlowResponse(
        transcription=transcription, instruction=instruction, result=result
    )


async def _read_manual_transcription(request: Request) -> str:
    try:
        body = await request.json()
    except ValueError as exc:
        raise RequestValidationError(
            [{"type": "json_invalid", "loc": ("body",), "msg": "Invalid JSON body."}]
        ) from exc
    try:
        return InstructionRequest.model_validate(body).transcription
    except ValidationError as exc:
        errors = exc.errors(include_url=False, include_context=False)
        raise RequestValidationError(
            [{**error, "loc": ("body", *error["loc"])} for error in errors]
        ) from exc


async def _transcribe_upload(request: Request) -> str:
    async with request.form() as form:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing audio file in form field 'file'.",
            )

        filename = upload.filename or ""
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in SUPPORTED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported audio format. Use one of: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}.",
            )

        audio = await upload.read()
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The audio file is empty.",
            )
        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="The audio file exceeds the 25 MB limit.",
            )

        language = normalize_transcription_language(form.get("language"))

    return await transcribe_audio(audio, filename, language)
