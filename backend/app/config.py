"""Application settings loaded from environment variables / .env file."""
import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

# Input validation limits
MIN_JD_CHARS = 40
MAX_JD_CHARS = 15000
