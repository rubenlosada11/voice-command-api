from functools import lru_cache

from groq import AsyncGroq

from src.app.core.config import get_settings


class GroqServiceError(Exception):
    """Groq could not be reached or rejected the request."""


@lru_cache
def get_groq_client() -> AsyncGroq:
    settings = get_settings()
    return AsyncGroq(
        api_key=settings.groq_api_key,
        timeout=settings.request_timeout_seconds,
        max_retries=1,
    )
