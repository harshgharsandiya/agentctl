"""Configuration settings and environment loading for agentctl."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MODEL_NAME: str = "openai/gpt-oss-20b"
MAX_STEPS: int = 30
SESSIONS_DIR: Path = Path("sessions")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
