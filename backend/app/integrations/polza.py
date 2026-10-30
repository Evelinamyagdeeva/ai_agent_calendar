from openai import OpenAI
import httpx

from app.config import settings


def get_llm() -> OpenAI:
    timeout = httpx.Timeout(60.0, connect=12.0)
    http_client = httpx.Client(trust_env=False, timeout=timeout)
    return OpenAI(
        base_url=settings.polza_ai_base_url,
        api_key=settings.polza_ai_api_key,
        http_client=http_client,
        max_retries=0,
        timeout=timeout,
    )
