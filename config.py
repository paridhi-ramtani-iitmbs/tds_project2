import os
import logging

logger = logging.getLogger("uvicorn")

# Collect all API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Server Settings
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8000))
USER_SECRET = os.getenv("USER_SECRET", "default_secret").strip()

# API Configuration Priority: Gemini > AIProxy > OpenAI
API_CONFIGS = []

if GEMINI_API_KEY:
    API_CONFIGS.append({
        "name": "Gemini",
        "api_key": GEMINI_API_KEY,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-1.5-flash-latest"
    })
    logger.info("✓ Gemini API configured")

if AIPROXY_TOKEN:
    API_CONFIGS.append({
        "name": "AIProxy",
        "api_key": AIPROXY_TOKEN,
        "base_url": "https://aiproxy.sanand.workers.dev/openai/v1",
        "model": "gpt-4o-mini"
    })
    logger.info("✓ AIProxy configured")

if OPENAI_API_KEY:
    API_CONFIGS.append({
        "name": "OpenAI",
        "api_key": OPENAI_API_KEY,
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini"
    })
    logger.info("✓ OpenAI API configured")

if not API_CONFIGS:
    raise ValueError("No API keys configured. Set at least one: GEMINI_API_KEY, AIPROXY_TOKEN, or OPENAI_API_KEY")

logger.info(f"Total {len(API_CONFIGS)} API(s) configured with fallback support")
