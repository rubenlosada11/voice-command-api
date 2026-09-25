from types import SimpleNamespace


class FakeGroq:
    """Stands in for AsyncGroq so tests never call the real API."""

    def __init__(self) -> None:
        self.llm_content: str | None = None
        self.llm_error: Exception | None = None
        self.transcript = ""
        self.stt_error: Exception | None = None
        self.chat_calls: list[dict] = []
        self.audio_calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=self._transcribe))

    async def _chat(self, **kwargs):
        self.chat_calls.append(kwargs)
        if self.llm_error:
            raise self.llm_error
        message = SimpleNamespace(content=self.llm_content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    async def _transcribe(self, **kwargs):
        self.audio_calls.append(kwargs)
        if self.stt_error:
            raise self.stt_error
        return SimpleNamespace(text=self.transcript)
