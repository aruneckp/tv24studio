import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv is optional
    pass


def _list(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True)

FEEDS = _list(
    "FEEDS",
    "https://feeds.bbci.co.uk/telugu/rss.xml,"
    "https://news.google.com/rss/search?q=Andhra+Pradesh&hl=te&gl=IN&ceid=IN:te",
)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

VOICES = {
    "female": os.getenv("VOICE_FEMALE", "te-IN-ShrutiNeural"),
    "male": os.getenv("VOICE_MALE", "te-IN-MohanNeural"),
}
VOICE_RATE = os.getenv("VOICE_RATE", "+0%")

CORS_ORIGINS = _list("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

CHANNEL_NAME = "TV24 స్టూడియో"
