import logging

from groq import NOT_GIVEN, APIError

from src.app.core.config import get_settings
from src.app.services.groq_client import GroqServiceError, get_groq_client

logger = logging.getLogger(__name__)


class EmptyTranscriptionError(Exception):
    """Whisper did not detect any speech in the audio."""


async def transcribe_audio(audio: bytes, filename: str, language: str | None) -> str:
    settings = get_settings()
    try:
        transcription = await get_groq_client().audio.transcriptions.create(
            model=settings.groq_transcription_model,
            file=(filename, audio),
            language=language or NOT_GIVEN,
            response_format="json",
            temperature=0,
        )
    except APIError as exc:
        logger.warning("Groq transcription request failed: %s", type(exc).__name__)
        raise GroqServiceError("The transcription request failed.") from exc

    text = transcription.text.strip()
    if not text:
        raise EmptyTranscriptionError("No speech was detected in the audio.")
    return text
