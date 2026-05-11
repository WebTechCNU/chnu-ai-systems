async def parse_requirements(text: str):
    prompt = f"""
    Convert these requirements into structured QA checks.

    Requirements:
    {text}

    Return JSON:
    [
      {{
        "id": "...",
        "description": "...",
        "category": "ui|accessibility|functional|seo|performance",
        "severity": "critical|major|minor"
      }}
    ]
    """