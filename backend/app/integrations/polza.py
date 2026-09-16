from openai import OpenAI

from app.config import settings


def get_llm() -> OpenAI:
    return OpenAI(
        base_url=settings.polza_ai_base_url,
        api_key=settings.polza_ai_api_key,
    )
