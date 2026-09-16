ORCHESTRATOR_PROMPT = """Ты оркестратор персонального агента развития. Пользователь один, говоришь по-русски.
Не выдумывай факты, которых нет в context pack. Выбери роль и работай через tools.
Роли: onboarding, roadmap, calendar, habits, review.
Если онбординг не завершён — сначала сферы и SMART-цели.
Календарь: только предлагай события, запись после подтверждения пользователя.
Цели всегда SMART, дедлайн обязателен.
"""

ROLE_PROMPTS = {
    "onboarding": """Роль: онбординг. Помоги выбрать сферы жизни (можно свои) и поставить SMART-цели.
Задавай короткие вопросы. Сохраняй сферы и цели через tools. Когда карта готова — update_profile onboarding_complete=true.""",
    "roadmap": """Роль: roadmap. Строй этапы с дедлайнами, задачами и ТЗ (brief).
При пересборке не удаляй смысл уже сделанного: completed/preserved этапы остаются в контексте.""",
    "calendar": """Роль: календарь. Понимай свободные фразы. Уточняй дату, длительность, сферу.
Проверяй конфликты и свободные окна. Создавай pending через propose_calendar_event.
Не утверждай, что событие уже в Google — только предложение.
Повторяющиеся события: recurrence RRULE, until если пользователь сказала когда закончить.""",
    "habits": """Роль: привычки. Предлагай реалистичный ритм под цели и инсайты (не обязательно каждый день).""",
    "review": """Роль: рефлексия и недельный обзор. Вопросы каждый раз новые, по задачам недели.
Учитывай оценки 1-10 и текст. Сохраняй рефлексию, обзор и инсайты. Комментируй темп целей.""",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": "Обновить профиль: TZ, рабочие часы, рефлексия, онбординг",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string"},
                    "work_start": {"type": "string"},
                    "work_end": {"type": "string"},
                    "work_days": {"type": "string"},
                    "onboarding_complete": {"type": "boolean"},
                    "reflection_weekday": {"type": "integer"},
                    "reflection_time": {"type": "string"},
                    "display_name": {"type": "string"},
                    "telegram_chat_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "upsert_area",
            "description": "Создать или обновить сферу жизни",
            "parameters": {
                "type": "object",
                "properties": {
                    "area_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": "Создать SMART-цель. deadline обязателен YYYY-MM-DD",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "deadline": {"type": "string"},
                    "area_id": {"type": "integer"},
                    "specific": {"type": "string"},
                    "measurable": {"type": "string"},
                    "achievable": {"type": "string"},
                    "relevant": {"type": "string"},
                    "success_criteria": {"type": "string"},
                },
                "required": ["title", "deadline"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_roadmap",
            "description": "Заменить активные этапы цели, done-этапы сохраняются",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "integer"},
                    "stages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "brief": {"type": "string"},
                                "deadline": {"type": "string"},
                                "tasks": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "details": {"type": "string"},
                                            "due_date": {"type": "string"},
                                        },
                                        "required": ["title"],
                                    },
                                },
                            },
                            "required": ["title"],
                        },
                    },
                },
                "required": ["goal_id", "stages"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_slots",
            "description": "Свободные окна в рабочих часах на горизонте days",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer"},
                    "duration_min": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_conflicts",
            "description": "Проверить пересечения и предложить альтернативы",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                },
                "required": ["start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_calendar_event",
            "description": "Черновик события. Запись только после approve пользователя.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "description": {"type": "string"},
                    "area_id": {"type": "integer"},
                    "goal_id": {"type": "integer"},
                    "habit_id": {"type": "integer"},
                    "recurrence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "RRULE строки, например RRULE:FREQ=WEEKLY;UNTIL=20261231T000000Z",
                    },
                },
                "required": ["title", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_habit",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "cadence": {"type": "string"},
                    "area_id": {"type": "integer"},
                    "goal_id": {"type": "integer"},
                    "notes": {"type": "string"},
                    "suggested": {"type": "boolean"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_habit",
            "parameters": {
                "type": "object",
                "properties": {
                    "habit_id": {"type": "integer"},
                    "day": {"type": "string"},
                    "done": {"type": "boolean"},
                    "note": {"type": "string"},
                },
                "required": ["habit_id", "day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_reflection",
            "parameters": {
                "type": "object",
                "properties": {
                    "week_start": {"type": "string"},
                    "energy": {"type": "integer"},
                    "productivity": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["week_start", "energy", "productivity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_weekly_review",
            "parameters": {
                "type": "object",
                "properties": {
                    "week_start": {"type": "string"},
                    "content": {"type": "string"},
                    "pace_notes": {"type": "string"},
                },
                "required": ["week_start", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Сохранить устойчивый факт о пользователе",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["content"],
            },
        },
    },
]
