import os
from pathlib import Path

# Points to backend/app/prompts
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt_file(filename: str) -> str:
    """Reads a text prompt from app/prompts/<filename>."""
    filepath = PROMPTS_DIR / filename
    if not filepath.exists():
        return ""
    return filepath.read_text(encoding="utf-8").strip()


def get_persona_prompt(persona_name: str) -> str:
    """
    Maps incoming persona string to the respective .txt file in app/prompts.
    """
    normalized = (persona_name or "").strip().lower()

    if "financial" in normalized:
        return load_prompt_file("financial_analyst.txt")
    elif "legal" in normalized:
        return load_prompt_file("legal_advisor.txt")
    elif "general" in normalized or normalized == "auto" or not normalized:
        return load_prompt_file("general_assistant.txt")

    return load_prompt_file("general_assistant.txt")