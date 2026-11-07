from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agents.context_pack import build_context_pack
from app.agents.prompts import ORCHESTRATOR_PROMPT, ROLE_PROMPTS, TOOLS
from app.agents.tools import execute_tool
from app.config import settings
from app.integrations.polza import get_llm
from app.services import conversations


def _chat(messages: list[dict], tools: bool = True):
    client = get_llm()
    kwargs = {
        "model": settings.polza_ai_model_name,
        "messages": messages,
        "max_tokens": 1024,
    }
    if tools:
        kwargs["tools"] = TOOLS
        kwargs["tool_choice"] = "auto"
    return client.chat.completions.create(**kwargs)


def _maybe_summarize(db: Session, session, history: list[dict]) -> None:
    if len(history) < 16:
        return
    try:
        resp = _chat(
            [
                {
                    "role": "system",
                    "content": "Суммируй диалог агента развития: цели, договорённости, открытые вопросы. Коротко.",
                },
                {"role": "user", "content": json.dumps(history[-24:], ensure_ascii=False)},
            ],
            tools=False,
        )
        text = resp.choices[0].message.content or ""
        conversations.update_summary(db, session, text)
    except Exception:
        pass


def run_agent(db: Session, user_text: str, channel: str = "web") -> dict:
    session = conversations.get_or_create_session(db, channel)
    conversations.add_message(db, session, "user", user_text)
    pack = build_context_pack(db)
    history = conversations.recent_messages(db, session, 20)
    system = (
        ORCHESTRATOR_PROMPT
        + "\n\n"
        + "\n\n".join(ROLE_PROMPTS.values())
        + "\n\nCONTEXT PACK:\n"
        + json.dumps(pack, ensure_ascii=False, default=str)[:8000]
    )
    if session.summary:
        system += "\n\nSESSION SUMMARY:\n" + session.summary
    messages = [{"role": "system", "content": system}] + history
    pending_ids: list[int] = []
    reply = ""
    if not settings.polza_ai_api_key:
        reply = "Нет POLZA_AI_API_KEY в .env — без него агент не отвечает."
    else:
        try:
            for _ in range(3):
                response = _chat(messages)
                choice = response.choices[0].message
                tool_calls = choice.tool_calls or []
                if tool_calls:
                    dumped = choice.model_dump(exclude_unset=True)
                    messages.append(dumped)
                    for tc in tool_calls:
                        args = json.loads(tc.function.arguments or "{}")
                        result = execute_tool(db, tc.function.name, args)
                        if tc.function.name == "propose_calendar_event":
                            try:
                                pending_ids.append(json.loads(result)["pending_id"])
                            except Exception:
                                pass
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
                    continue
                reply = choice.content or "Готово."
                break
        except Exception:
            reply = "Сейчас не могу ответить."
    if not reply:
        reply = "Сейчас не могу ответить."
    conversations.add_message(db, session, "assistant", reply)
    _maybe_summarize(db, session, history + [{"role": "assistant", "content": reply}])
    return {"reply": reply, "pending_ids": pending_ids, "session_id": session.id}
