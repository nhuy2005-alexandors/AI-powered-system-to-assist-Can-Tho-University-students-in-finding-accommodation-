from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Engine

from ...config import settings
from .providers import (
    E5EmbeddingProvider,
    FallbackResponseGenerator,
    GeminiGenerator,
    GroundedTemplateGenerator,
    OllamaQwenGenerator,
)
from .repo import ChatRepository
from .schemas import ChatAskRequest, ChatAskResponse
from .service import ChatService

router = APIRouter(prefix="/chat", tags=["chatbot"])
_service: ChatService | None = None


def init_chatbot(engine: Engine) -> None:
    global _service
    providers = []
    degraded_reasons: list[str] = []

    if settings.chatbot_llm_provider in ("auto", "qwen"):
        providers.append(
            OllamaQwenGenerator(
                settings.ollama_base_url,
                settings.ollama_model,
                settings.chatbot_llm_timeout_seconds,
            )
        )

    if settings.chatbot_llm_provider in ("auto", "gemini"):
        if settings.gemini_api_key:
            providers.append(
                GeminiGenerator(
                    settings.gemini_api_key,
                    settings.gemini_model,
                    settings.gemini_base_url,
                    settings.chatbot_llm_timeout_seconds,
                )
            )
        elif settings.chatbot_llm_provider == "gemini":
            degraded_reasons.append("Gemini được chọn nhưng GEMINI_API_KEY chưa cấu hình")

    _service = ChatService(
        ChatRepository(engine),
        E5EmbeddingProvider(settings.chatbot_embedding_model),
        FallbackResponseGenerator(
            providers,
            GroundedTemplateGenerator(),
            initial_degraded_reasons=degraded_reasons,
        ),
        confidence_threshold=settings.chatbot_confidence_threshold,
        max_results=settings.chatbot_max_results,
    )


def get_service() -> ChatService:
    if _service is None:
        raise HTTPException(503, "Chatbot chưa khởi tạo")
    return _service


@router.post("/ask", response_model=ChatAskResponse)
def ask_chatbot(
    body: ChatAskRequest,
    service: ChatService = Depends(get_service),
):
    return service.ask(body)
