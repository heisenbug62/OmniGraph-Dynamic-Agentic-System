import os
import logging
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application Configs
    APP_NAME: str = "Dynamic Multi-Agent System"
    ENVIRONMENT: str = "development"

    # API Keys
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Primary Model and Fallbacks (Resilience Configuration)
    MODEL_NAME: str = "openai/gpt-4o-mini"
    FALLBACK_MODELS: str = "google/gemini-2.5-flash,anthropic/claude-3.5-haiku"
    MAX_RETRIES: int = 2
    REQUEST_TIMEOUT: float = 60.0

    # Pinecone Vector DB Settings
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "agentic-rag"
    DEFAULT_TOP_K: int = 4

    # Generation Parameters
    DEFAULT_TEMPERATURE: float = 0.2
    MAX_OUTPUT_TOKENS: int = 1000

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Resolve API Key & OpenRouter Base URL
api_key = (
    settings.OPENROUTER_API_KEY
    or settings.OPENAI_API_KEY
    or os.getenv("OPENROUTER_API_KEY")
    or os.getenv("OPENAI_API_KEY")
)

base_url = (
    "https://openrouter.ai/api/v1"
    if (settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY"))
    else None
)


def get_chat_model(
    model: Optional[str] = None,
    fallback_models: Optional[Union[List[str], str]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    streaming: bool = False,
    **kwargs,
) -> BaseChatModel | Runnable:
    """
    Creates a resilient ChatOpenAI instance configured with automatic fallbacks
    and retries across multiple LLM providers via OpenRouter.
    """
    primary_model = model or settings.MODEL_NAME or "openai/gpt-4o-mini"
    temp = settings.DEFAULT_TEMPERATURE if temperature is None else temperature
    tokens = settings.MAX_OUTPUT_TOKENS if max_tokens is None else max_tokens

    # Parse fallback models
    raw_fallbacks = fallback_models if fallback_models is not None else settings.FALLBACK_MODELS
    if isinstance(raw_fallbacks, str):
        fallback_list = [m.strip() for m in raw_fallbacks.split(",") if m.strip()]
    elif isinstance(raw_fallbacks, list):
        fallback_list = [m.strip() for m in raw_fallbacks if m.strip()]
    else:
        fallback_list = []

    # Filter out primary model from fallbacks to avoid duplicate attempts
    fallback_list = [m for m in fallback_list if m != primary_model]

    primary_llm = ChatOpenAI(
        model=primary_model,
        api_key=api_key,
        base_url=base_url,
        temperature=temp,
        max_tokens=tokens,
        streaming=streaming,
        max_retries=settings.MAX_RETRIES,
        timeout=settings.REQUEST_TIMEOUT,
        **kwargs,
    )

    if not fallback_list:
        return primary_llm

    fallback_llms = [
        ChatOpenAI(
            model=fb_model,
            api_key=api_key,
            base_url=base_url,
            temperature=temp,
            max_tokens=tokens,
            streaming=streaming,
            max_retries=settings.MAX_RETRIES,
            timeout=settings.REQUEST_TIMEOUT,
            **kwargs,
        )
        for fb_model in fallback_list
    ]

    return primary_llm.with_fallbacks(fallback_llms)


# Global ChatOpenAI Instance pointing to OpenRouter with fallback support
llm = get_chat_model()